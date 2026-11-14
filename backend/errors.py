"""Errors raised by the engine; main.py maps them to HTTP responses."""


class HandoverError(Exception):
    status_code = 500

    def __init__(self, detail: str = ""):
        super().__init__(detail)
        self.detail = detail or self.__class__.__name__


class BadRequest(HandoverError):
    status_code = 400


class Unauthorized(HandoverError):
    status_code = 401


class Forbidden(HandoverError):
    status_code = 403


class NotFound(HandoverError):
    status_code = 404
