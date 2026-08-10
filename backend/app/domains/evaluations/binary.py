"""二进制响应辅助：不套 JSON Envelope（契约 §7.1 / §8.5 / §8.4 download）。"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi.responses import RedirectResponse, Response


def _ascii_download_name(file_name: str) -> str:
    leaf_name = PurePosixPath(file_name.replace("\\", "/")).name
    path = PurePosixPath(leaf_name)
    suffix = path.suffix.lower()
    safe_suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
    normalized_stem = unicodedata.normalize("NFKD", path.stem).encode("ascii", "ignore").decode("ascii")
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", normalized_stem).strip(" -")
    if safe_stem and any(character.isalnum() for character in safe_stem):
        return f"{safe_stem}{safe_suffix}"
    return f"download{safe_suffix}"


def binary_file_response(
    *,
    content: bytes,
    file_name: str,
    content_type: str,
    sha256: str | None = None,
) -> Response:
    digest = sha256 or hashlib.sha256(content).hexdigest()
    encoded = quote(file_name, safe="")
    ascii_name = _ascii_download_name(file_name)
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}",
            "Content-Type": content_type,
            "X-File-Sha256": digest,
        },
    )


def binary_redirect(url: str, *, sha256: str | None = None) -> RedirectResponse:
    headers = {}
    if sha256:
        headers["X-File-Sha256"] = sha256
    return RedirectResponse(url=url, status_code=302, headers=headers)
