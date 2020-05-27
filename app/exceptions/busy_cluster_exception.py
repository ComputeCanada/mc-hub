from exceptions.invalid_usage_exception import InvalidUsageException


class BusyClusterException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster is currently busy", 400)
