"""
app/utils/responses.py

Standardized API response wrapper.

All API responses follow this shape:
    {
        "success": true | false,
        "message": "Human-readable message",
        "data": { ... } | null
    }

This ensures the frontend always has a predictable response contract.
"""

from typing import Any

from fastapi.responses import ORJSONResponse


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> ORJSONResponse:
    """
    Return a standardized success response.

    Args:
        data: The response payload (dict, list, or any serializable type).
        message: A human-readable success message.
        status_code: HTTP status code (default 200).

    Returns:
        ORJSONResponse with success=True envelope.
    """
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
        },
    )


def error_response(
    message: str = "An error occurred",
    status_code: int = 400,
    errors: Any = None,
) -> ORJSONResponse:
    """
    Return a standardized error response.

    Args:
        message: A human-readable error message.
        status_code: HTTP status code (default 400).
        errors: Optional detailed error info (e.g., validation errors).

    Returns:
        ORJSONResponse with success=False envelope.
    """
    content: dict[str, Any] = {
        "success": False,
        "message": message,
        "data": None,
    }
    if errors is not None:
        content["errors"] = errors

    return ORJSONResponse(status_code=status_code, content=content)
