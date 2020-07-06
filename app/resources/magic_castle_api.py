from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle import MagicCastle
from models.cluster_status_code import ClusterStatusCode


class MagicCastleAPI(ApiView):
    def get(self, hostname, status=False):
        if hostname:
            magic_castle = MagicCastle(hostname)
            if status:
                status = magic_castle.get_status()
                if status == ClusterStatusCode.NOT_FOUND:
                    return {
                        "status": status.value,
                    }
                else:
                    progress = magic_castle.get_progress()
                    if progress is None:
                        return {"status": status.value}
                    else:
                        return {"status": status.value, "progress": progress}
            else:
                try:
                    return magic_castle.get_state()
                except InvalidUsageException as e:
                    return e.get_response()
        else:
            return [
                {
                    "cluster_name": magic_castle.get_cluster_name(),
                    "domain": magic_castle.get_domain(),
                    "hostname": magic_castle.get_hostname(),
                    "status": magic_castle.get_status().value,
                }
                for magic_castle in MagicCastle.all()
            ]

    def post(self, hostname, apply=False):
        if apply:
            magic_castle = MagicCastle(hostname)
            try:
                magic_castle.apply()
                return {}
            except InvalidUsageException as e:
                return e.get_response()
        else:
            magic_castle = MagicCastle()
            json_data = request.get_json()
            if not json_data:
                return {"message": "No json data was provided"}, 400

            try:
                magic_castle.load_configuration(json_data)
                magic_castle.plan_creation()
                return {}
            except InvalidUsageException as e:
                return e.get_response()

    def put(self, hostname):
        magic_castle = MagicCastle(hostname)
        json_data = request.get_json()

        if not json_data:
            return {"message": "No json data was provided"}, 400

        try:
            magic_castle.load_configuration(json_data)
            magic_castle.plan_modification()
            return {}
        except InvalidUsageException as e:
            return e.get_response()

    def delete(self, hostname):
        magic_castle = MagicCastle(hostname)
        try:
            magic_castle.plan_destruction()
            return {}
        except InvalidUsageException as e:
            return e.get_response()
