import logging


class ServerException(Exception):
    DEFAULT_STATUS_CODE = 500

    def __init__(
        self,
        message: str,
        status_code: int = DEFAULT_STATUS_CODE,
        *,
        additional_details: str = "",
    ):
        """
        Instantiates an exception related to an error originating from the server.

        :param status_code: The HTTP response status code.
        :param message: The error message, which will be logged and displayed to the user.
        :param additional_details: Additional details which will be logged but not shown to the user.
        """
        Exception.__init__(self, message)
        self.status_code = status_code
        self.message = message
        logging.error(f"{message} {additional_details}")

    def get_response(self):
        return {"message": self.message}, self.status_code


class PuppetTimeoutException(ServerException):
    def __init__(self):
        ServerException.__init__(self, "Puppet provisioning timed out.")


class PlanException(ServerException):
    def __init__(
        self,
        message: str = "An error occurred when planning changes.",
        *,
        additional_details: str = "",
    ):
        """
        Instantiates an exception related to an error happening during the cluster plan phase.

        :param message: The error message, which will be logged and displayed to the user.
        :param additional_details: Additional details which will be logged but not shown to the user.
        """
        ServerException.__init__(self, message, additional_details=additional_details)
