from flask import request
from flask.views import MethodView
from flask import make_response
from database.database_manager import DatabaseManager
from models.auth_type import AuthType
from models.user.anonymous_user import AnonymousUser
from models.user.authenticated_user import AuthenticatedUser
from exceptions.unauthenticated_exception import UnauthenticatedException
from exceptions.invalid_usage_exception import InvalidUsageException
from os import environ
import json

DEFAULT_RESPONSE_CODE = 200


def output_json(route_handler):
    def decorator(*args, **kwargs):
        response = route_handler(*args, **kwargs)
        if type(response) == tuple:
            data, response_code = response
        else:
            data, response_code = response, DEFAULT_RESPONSE_CODE
        headers = {"Content-Type": "application/json"}
        return make_response(json.dumps(data), response_code, headers)

    return decorator


def handle_invalid_usage(route_handler):
    def decorator(*args, **kwargs):
        try:
            return route_handler(*args, **kwargs)
        except InvalidUsageException as e:
            return e.get_response()

    return decorator


def compute_current_user(route_handler):
    def decorator(*args, **kwargs):
        auth_type = AuthType(environ.get("AUTH_TYPE"))
        with DatabaseManager.connect() as database_connection:
            if auth_type == AuthType.SAML:
                try:
                    # Note: Request headers are interpreted as ISO Latin 1 encoded strings.
                    # Therefore, special characters and accents in givenName and surname are not correctly decoded. 
                    user = AuthenticatedUser(
                        database_connection,
                        edu_person_principal_name=request.headers[
                            "eduPersonPrincipalName"
                        ],
                        given_name=request.headers["givenName"],
                        surname=request.headers["surname"],
                        mail=request.headers["mail"],
                    )
                except KeyError:
                    # Missing an authentication header
                    raise UnauthenticatedException
            else:
                user = AnonymousUser(database_connection)
            return route_handler(user, *args, **kwargs)

    return decorator


class ApiView(MethodView):
    decorators = [
        compute_current_user,
        handle_invalid_usage,
        output_json,
    ]
