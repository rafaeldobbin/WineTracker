from __future__ import annotations


class DomainError(Exception):
    """Base for expected business-rule failures. ``code`` is a stable i18n key."""

    code = "error.generic"
    status = 400

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class NotFoundError(DomainError):
    code = "error.not_found"
    status = 404


class ConflictError(DomainError):
    code = "error.conflict"
    status = 409


class AuthenticationError(DomainError):
    code = "error.invalid_credentials"
    status = 401


class EmailTakenError(ConflictError):
    code = "error.email_taken"
