from flask import request
from flask.views import MethodView
from flask import make_response
from database.database_manager import DatabaseManager
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


def open_database_connection(route_handler):
    def decorator(*args, **kwargs):
        with DatabaseManager.connect() as database_connection:
            return route_handler(database_connection, *args, **kwargs)

    return decorator


class ApiView(MethodView):
    decorators = [open_database_connection, output_json]
