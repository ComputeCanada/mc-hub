from exceptions.invalid_usage_exception import InvalidUsageException


class ClusterNotFoundException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster does not exist", 400)
