from __future__ import annotations

from urllib.parse import quote

from app.domains.evaluations.binary import binary_file_response


def test_binary_response_encodes_unicode_filename_without_latin1_failure() -> None:
    file_name = "\u6df1\u5733\u653f\u52a1\u4e91\u9879\u76ee-\u8bc4\u6807\u62a5\u544a.pdf"

    response = binary_file_response(
        content=b"%PDF-test",
        file_name=file_name,
        content_type="application/pdf",
    )

    disposition = response.headers["content-disposition"]
    disposition.encode("latin-1")
    assert 'filename="download.pdf"' in disposition
    assert f"filename*=UTF-8''{quote(file_name, safe='')}" in disposition
    assert response.headers["x-file-sha256"]


def test_binary_response_sanitizes_mixed_ascii_fallback() -> None:
    response = binary_file_response(
        content=b"PK-test",
        file_name='E2E \u6280\u672f\u62a5\u544a "\u6700\u7ec8\u7248".docx',
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    disposition = response.headers["content-disposition"]
    assert 'filename="E2E.docx"' in disposition
    assert "\r" not in disposition and "\n" not in disposition


def test_binary_response_does_not_copy_path_or_control_characters_to_ascii_fallback() -> None:
    file_name = "../unsafe\\report\r\nX-Injected: yes.pdf"

    response = binary_file_response(
        content=b"%PDF-test",
        file_name=file_name,
        content_type="application/pdf",
    )

    disposition = response.headers["content-disposition"]
    assert 'filename="report-X-Injected-yes.pdf"' in disposition
    assert "\r" not in disposition and "\n" not in disposition
    assert f"filename*=UTF-8''{quote(file_name, safe='')}" in disposition
