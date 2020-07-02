from exceptions.invalid_usage_exception import InvalidUsageException


class StateNotFoundException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(
            self, "The terraform state file was not found", 400
        )

