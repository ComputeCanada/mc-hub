class InvalidUsageException(Exception):
    DEFAULT_STATUS_CODE = 400

    def __init__(self, message: str, status_code: int = DEFAULT_STATUS_CODE):
        Exception.__init__(self)
        self.status_code = status_code
        self.message = message

    def get_response(self):
        return {"message": self.message}, self.status_code


class BusyClusterException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster is busy", 400)


class ClusterExistsException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster already exists", 400)


class ClusterNotFoundException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster does not exist", 400)


class PlanNotCreatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(
            self, "The terraform plan for this cluster does not exist", 400
        )


class UnauthenticatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "You need to be authenticated", 400)
