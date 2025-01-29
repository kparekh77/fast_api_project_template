import http
import json
from typing import Dict, Optional, Any, List

from fastapi import Response


class ProblemException(Exception):
    """
    An RFC 7807 Problem exception.

    This models a "problem" as defined in RFC 7807 (https://tools.ietf.org/html/rfc7807).
    It is intended to be subclassed to create application-specific instances of
    problems which, when raised, can be trapped by the application error handler
    and converted into HTTP responses with properly-formatted JSON response bodies.

    Default values are applied to the `type`, `status`, and `title` field if
    they are left unspecified.

    It is generally not recommended to modify the Problem instance members
    post-initialization, but nothing prevents you from doing so if you need
    more granular control over how/when values are set.
    """

    headers: Dict[str, str] = {}

    def __init__(
        self,
        _type: Optional[str] = None,
        title: Optional[str] = None,
        status: Optional[int] = None,
        detail: Optional[str] = None,
        instance: Optional[str] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.type: str = _type or "exception:problem"
        self.status: int = status or 500
        self.title: str = title or http.HTTPStatus(self.status).phrase
        self.detail: Optional[str] = detail
        self.instance: Optional[str] = instance
        self.errors: Optional[Dict[str, Any]] = errors

    def to_bytes(self) -> bytes:
        """
        Render the Problem as JSON-serialized bytes.

        Returns:
            The JSON-serialized bytes representing the Problem response.
        """
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

    def to_dict(self) -> Dict[str, Any]:
        """
        Get a dictionary representation of the Problem response.

        Returns:
            A dictionary representation of the Problem exception. This can be serialized
            out to JSON and used as the response body.
        """
        d = {}

        if self.type:
            d["type"] = str(self.type)
        if self.title:
            d["title"] = str(self.title)
        if self.status:
            d["status"] = int(self.status)
        if self.detail:
            d["detail"] = str(self.detail)
        if self.instance:
            d["instance"] = str(self.instance)
        if self.errors:
            d["errors"] = self.errors

        return d

    def to_response(self) -> Response:
        """
        Get a response object representation of the Problem response.

        Returns:
            A response object representation of the Problem exception. This can be used
            as the response object.
        """
        return Response(
            content=self.to_bytes(),
            media_type="application/problem+json",
            status_code=self.status,
        )

    def __str__(self) -> str:
        return str(f"Problem:<{self.to_dict()}>")

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProblemException):
            return False
        return self.__dict__ == other.__dict__
