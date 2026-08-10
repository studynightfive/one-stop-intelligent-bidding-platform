"""无第三方依赖的最小 PDF 字节，支持简体中文 CID 字体。"""

from __future__ import annotations


def build_simple_pdf(lines: list[str]) -> bytes:
    """生成可被常见阅读器打开的 UTF-16BE 简易 PDF。"""
    text_ops = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for idx, line in enumerate(lines):
        encoded = str(line).encode("utf-16-be").hex().upper()
        if idx == 0:
            text_ops.append(f"<{encoded}> Tj")
        else:
            text_ops.append("T*")
            text_ops.append(f"<{encoded}> Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n")
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >>endobj\n"
    )
    objects.append(
        b"6 0 obj<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo<< /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> >>endobj\n"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
    return bytes(out)
