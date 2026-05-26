from __future__ import annotations
import re
from typing import Callable
from fastapi.routing import APIRoute
from fastapi import Request, Response, HTTPException

ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.\:\s\(\)\/]+$")
FORBIDDEN_SUBSTRINGS = ["'", '"', ";", "--", "/*", "*/", "//", "{", "}", "$"]

class InputValidationRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_handler = super().get_route_handler()
        async def route_handler(request: Request) -> Response:
            # Validate query parameters
            for name, value in request.query_params.items():
                if "id" in name.lower():
                    if not ID_REGEX.match(value) or any(f in value for f in FORBIDDEN_SUBSTRINGS):
                        raise HTTPException(400, f"Malformed {name} parameter: forbidden characters detected.")
            # Validate path parameters
            for name, value in request.path_params.items():
                if "id" in name.lower() or name in ("ac_id", "booth_id"):
                    if not ID_REGEX.match(value) or any(f in value for f in FORBIDDEN_SUBSTRINGS):
                        raise HTTPException(400, f"Malformed {name} parameter: forbidden characters detected.")
            return await original_handler(request)
        return route_handler
