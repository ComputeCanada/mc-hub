from exceptions.invalid_usage_exception import InvalidUsageException


class UnauthenticatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "You need to be authenticated", 400)

