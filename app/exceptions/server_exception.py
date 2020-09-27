class ServerException(Exception):
    DEFAULT_STATUS_CODE = 400

    def __init__(self, message: str, status_code: int = DEFAULT_STATUS_CODE):
        Exception.__init__(self)
        self.status_code = status_code
        self.message = message

    def get_response(self):
        return {"message": self.message}, self.status_code


class PuppetTimeoutException(ServerException):
    def __init__(self):
        ServerException.__init__(self, "Puppet provisioning timed out", 400)


class StateNotFoundException(ServerException):
    def __init__(self):
        ServerException.__init__(self, "The terraform state file was not found", 400)
