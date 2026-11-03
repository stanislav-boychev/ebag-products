"""Errors the services raise. They know nothing about HTTP; main.py maps them to status codes."""


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class InvalidInput(Exception):
    """A body field is well-formed but not acceptable, such as a category that doesn't exist."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
