from exceptions.invalid_usage_exception import InvalidUsageException


class ClusterExistsException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(self, "This cluster already exists", 400)
