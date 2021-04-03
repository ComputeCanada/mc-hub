class InvalidUsageException(Exception):
    DEFAULT_STATUS_CODE = 400

    def __init__(self, message: str, status_code: int = DEFAULT_STATUS_CODE):
        """
        Instantiates an exception related to an error originating from the user.

        :param message: The error message, which will be displayed to the user.
        :param status_code: The HTTP response status code.
        """
        Exception.__init__(self, message)
        self.status_code = status_code
        self.message = message

    def get_response(self):
        return {"message": self.message}, self.status_code


class BusyClusterException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster is busy.")


class ClusterExistsException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster already exists.")


class ClusterNotFoundException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster does not exist.")


class PlanNotCreatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(
            self, "The terraform plan for this cluster does not exist."
        )


class UnauthenticatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "You need to be authenticated.")
