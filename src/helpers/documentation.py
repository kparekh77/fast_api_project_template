import random
import string
from collections.abc import MutableMapping
from enum import Enum
from typing import Any

from pydantic import BaseModel
from starlette.requests import Request


def response(
    example: dict = None,
    description: str = None,
    model: Any = None,
) -> dict:
    result = {}

    if model:
        result["model"] = model

    if description:
        result["description"] = description

    if example:
        result["content"] = {"application/json": {"example": example}}

    return result


def request(
    summary: str = None,
    description: str = None,
    value: BaseModel = None,
) -> dict:
    result = {}

    if summary:
        result["summary"] = summary

    if description:
        result["description"] = description

    if value:
        result["value"] = value.model_dump_json(exclude_none=True)

    return result


def request_obj(path: str = None) -> Request:
    if path is None:
        path = f"/{''.join(random.choices(string.ascii_letters + string.digits, k=10))}"
    return Request({"type": "http", "_url": {"path": path}, "path": path, "headers": []})


def exception_obj(message: str = None) -> Exception:
    if message is None:
        message = "An unexpected error occurred while processing the request."
    return Exception(message)


def convert_enums_to_values(data: MutableMapping) -> dict:
    """
    Recursively converts all Enum keys and values in a dictionary
    to their primitive values (Enum.value).

    :param data: A dictionary potentially containing Enum keys and/or values.
    :return: A dictionary with all Enum instances converted to their values.
    """
    result = {}
    for key, value in data.items():
        if isinstance(key, Enum):
            key = key.value
        if isinstance(value, Enum):
            value = value.value
        elif isinstance(value, MutableMapping):
            value = convert_enums_to_values(value)
        result[key] = value
    return result
