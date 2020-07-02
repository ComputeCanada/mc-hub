from exceptions.invalid_usage_exception import InvalidUsageException


class PlanNotCreatedException(InvalidUsageException):
    def __init__(self):
        InvalidUsageException.__init__(
            self, "The terraform plan for this cluster does not exist", 400
        )

