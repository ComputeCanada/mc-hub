from exceptions.server_exception import ServerException

class PuppetTimeoutException(ServerException):
    def __init__(self):
        ServerException.__init__(self, "Puppet provisioning timed out", 400)

