"""二进制响应辅助：不套 JSON Envelope（契约 §7.1 / §8.5 / §8.4 download）。"""

from __future__ import annotations

import hashlib
from urllib.parse import quote

from fastapi.responses import RedirectResponse, Response


def binary_file_response(
    *,
    content: bytes,
    file_name: str,
    content_type: str,
    sha256: str | None = None,
) -> Response:
    digest = sha256 or hashlib.sha256(content).hexdigest()
    encoded = quote(file_name)
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{file_name}\"; filename*=UTF-8''{encoded}",
            "Content-Type": content_type,
            "X-File-Sha256": digest,
        },
    )


def binary_redirect(url: str, *, sha256: str | None = None) -> RedirectResponse:
    headers = {}
    if sha256:
        headers["X-File-Sha256"] = sha256
    return RedirectResponse(url=url, status_code=302, headers=headers)
