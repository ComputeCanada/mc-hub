import json
import re

from os import getlogin

from flask import request
from flask.views import MethodView
from flask import make_response

from ..configuration import config
from ..database import db
from ..models.auth_type import AuthType
from ..models.user import LocalUser, SAMLUser, UserORM
from ..exceptions.invalid_usage_exception import (
    UnauthenticatedException,
    InvalidUsageException,
)
from ..exceptions.server_exception import *


AUTH_HEADER_PAT = re.compile(r"token\s+(.+)", re.IGNORECASE)

DEFAULT_RESPONSE_CODE = 200


def output_json(route_handler):
    """
    Creates a decorator that serializes the response data from the return value of the
    route handler to a JSON string.

    :param route_handler:  The Flask route handler function.
    :return: The decorator that serializes the response to JSON.
    """

    def decorator(*args, **kwargs):
        response = route_handler(*args, **kwargs)
        if type(response) == tuple:
            data, response_code = response
        else:
            data, response_code = response, DEFAULT_RESPONSE_CODE
        headers = {"Content-Type": "application/json"}
        return make_response(json.dumps(data), response_code, headers)

    return decorator


def handle_exceptions(route_handler):
    """
    Creates a decorator that catches server and user exceptions and injects the error
    message in the response.

    :param route_handler: The Flask route handler function.
    :return: The decorator that handles exceptions.
    """

    def decorator(*args, **kwargs):
        try:
            return route_handler(*args, **kwargs)
        except (InvalidUsageException, ServerException) as e:
            return e.get_response()

    return decorator


def compute_current_user(route_handler):
    """
    Creates a decorator used to pass the current User object as a parameter
    to the route handler.

    If the authentication type is SAML, an SAMLUser object will be passed.
    Otherwise, if the authentication type is NONE, an LocalUser object will
    be passed.

    :param route_handler: The Flask route handler function.
    :return: The decorator that modifies the route handler to have the current user as a parameter.
    """

    def decorator(*args, **kwargs):
        # While the AuthType won't change during the life of the application
        # defining auth_type in compute_current_user context leads to problem
        # with the unit tests where both NONE and SAML are used.
        auth_type = config["auth_type"]
        headers = request.headers
        if AuthType.TOKEN in auth_type and "Authorization" in headers:
            m = AUTH_HEADER_PAT.match(headers["Authorization"])
            if m:
                user_token = m.group(1)
                if user_token == config["token"]:
                    user = LocalUser()
                else:
                    raise UnauthenticatedException
        elif AuthType.SAML in auth_type and "eduPersonPrincipalName" in headers:
            try:
                # Note: Request headers are interpreted as ISO Latin 1 encoded strings.
                # Therefore, special characters and accents in givenName and surname
                # are not correctly decoded.
                scoped_id = headers["eduPersonPrincipalName"]
                orm = UserORM.query.filter_by(scoped_id=scoped_id).first()
                if orm is None:
                    orm = UserORM(scoped_id=scoped_id)
                user = SAMLUser(
                    orm=orm,
                    edu_person_principal_name=scoped_id,
                    given_name=headers["givenName"],
                    surname=headers["surname"],
                    mail=headers["mail"],
                    ssh_public_key=headers.get("sshPublicKey", ""),
                )
            except KeyError:
                # Missing an authentication header
                raise UnauthenticatedException
        elif AuthType.NONE in auth_type:
            scoped_id = getlogin() + "@localhost"
            orm = UserORM.query.filter_by(scoped_id=scoped_id).first()
            if orm is None:
                orm = UserORM(scoped_id=scoped_id)
            user = LocalUser(orm=orm)
        else:
            raise UnauthenticatedException
        return route_handler(user, *args, **kwargs)

    return decorator


class ApiView(MethodView):
    """
    Configures all child classes to use the default decorators on all route handlers.
    """

    decorators = [
        compute_current_user,
        handle_exceptions,
        output_json,
    ]
