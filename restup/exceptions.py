
from . import constants


class RestUpError(Exception):
    pass


class HttpError(RestUpError):

    status = constants.ERROR
    msg = "Application Error."

    def __init__(self, msg=None):
        if not msg:
            msg = self.__class__.msg
        super(HttpError, self).__init__(msg)


class BadRequest(HttpError):
    status = constants.BAD_REQUEST
    msg = "Bad Request"


class Unauthorized(HttpError):
    status = constants.UNAUTHORIZED
    msg = "Unauthorized"


class Forbidden(HttpError):
    status = constants.FORBIDDEN
    msg = "Forbidden"


class NotFound(HttpError):
    status = constants.NOT_FOUND
    msg = "Not Found"


class NotAllowed(HttpError):
    status = constants.METHOD_NOT_ALLOWED
    msg = "Method Not Allowed"


class NotImplemented(HttpError):
    status = constants.NOT_IMPLEMENTED
    msg = "Method not Implemented"
