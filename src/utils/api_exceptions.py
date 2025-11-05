class ApiErrorBase(Exception):
    """Base exception for all API errors."""

    pass


class NetworkError(ApiErrorBase):
    """Raised when there is a network-related error (e.g., DNS failure, refused connection)."""

    pass


class ServerError(ApiErrorBase):
    """Raised when the server returns a 5xx error."""

    pass


class AuthenticationError(ApiErrorBase):
    """Raised when there is an authentication error (e.g., invalid token)."""

    pass


class ApiError(ApiErrorBase):
    """Raised when the API returns an unexpected response (e.g., 4xx client error, invalid data)."""

    pass
