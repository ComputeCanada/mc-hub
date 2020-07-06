from flask import request
from flask.views import MethodView
from flask import make_response
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


class ApiView(MethodView):
    decorators = [output_json]
