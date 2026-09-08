"""
doc_processing.chunking
========================
Nhận list "parsed block" (output của parsing.parse_document()) và cắt
thành chunks theo 1 trong 2 chiến lược, sau đó lưu ra JSON trong thư mục
`app/doc_processing/doc/` (xem OUTPUT_CHUNKING_DIR bên dưới).

Lưu ý: app/model/document.py hiện CHƯA có field department/access_level
(RBAC chưa được model hoá), nên chunk ở đây cũng chưa có 2 field đó. Khi
Document model được bổ sung RBAC, thêm lại 2 field tương ứng trong
chunk_blocks() bên dưới.
"""

from __future__ import annotations

import json
from pathlib import Path

# backend/app/doc_processing/chunking.py -> parent = doc_processing/
OUTPUT_CHUNKING_DIR = Path(__file__).resolve().parent / "doc"


def _split_fixed_overlap(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chiến lược 1: cắt cố định theo số ký tự, có overlap giữa các chunk."""
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        pieces.append(text[start:end])
        start = end - overlap
    return pieces


def _split_recursive_paragraph(text: str, max_chars: int = 500) -> list[str]:
    """Chiến lược 2: cắt theo đoạn văn, gộp đoạn ngắn lại cho đến gần max_chars."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    pieces: list[str] = []
    buffer = ""
    for p in paragraphs:
        if len(buffer) + len(p) <= max_chars:
            buffer = f"{buffer}\n{p}".strip()
        else:
            if buffer:
                pieces.append(buffer)
            buffer = p
    if buffer:
        pieces.append(buffer)
    return pieces


_STRATEGIES = {
    "fixed_overlap": _split_fixed_overlap,
    "recursive_paragraph": _split_recursive_paragraph,
}


def chunk_blocks(parsed_blocks: list[dict], strategy: str = "fixed_overlap") -> list[dict]:
    """
    Args:
        parsed_blocks: output của parsing.parse_document() - mỗi block có
            {document_id, page, text}.
        strategy: "fixed_overlap" hoặc "recursive_paragraph".

    Returns:
        list[dict]: mỗi chunk có {chunk_id, document_id, content, page,
        chunk_index, char_count, strategy}.
    """
    if strategy not in _STRATEGIES:
        raise ValueError(f"Chiến lược không tồn tại: {strategy!r}. Chọn 1 trong {list(_STRATEGIES)}")

    split_fn = _STRATEGIES[strategy]
    chunks: list[dict] = []
    for block in parsed_blocks:
        pieces = split_fn(block["text"])
        for i, piece in enumerate(pieces):
            chunks.append({
                "chunk_id": f"doc{block['document_id']}_p{block['page']}_c{i:03d}",
                "document_id": block["document_id"],
                "content": piece,
                "page": block["page"],
                "chunk_index": i,
                "char_count": len(piece),
                "strategy": strategy,
            })
    return chunks


def save_chunks(chunks: list[dict], document_id: int, out_dir: Path | str = OUTPUT_CHUNKING_DIR) -> Path:
    """Ghi chunks ra `output_chunking/{document_id}_chunking.json`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{document_id}_chunking.json"
    out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def chunk_and_save(parsed_blocks: list[dict], document_id: int, strategy: str = "fixed_overlap") -> Path:
    """Tiện ích gộp: chunk rồi lưu luôn ra file - dùng trong pipeline end-to-end."""
    chunks = chunk_blocks(parsed_blocks, strategy=strategy)
    return save_chunks(chunks, document_id)


if __name__ == "__main__":
    fake_blocks = [{
        "document_id": 1,
        "page": 1,
        "text": "Nhan vien thu viec duoc nghi phep 2 ngay moi thang.\nQuy dinh ap dung tu 2024.",
    }]
    result = chunk_blocks(fake_blocks, strategy="recursive_paragraph")
    out_path = save_chunks(result, document_id=1)
    print(f"Đã lưu {len(result)} chunk vào {out_path}")
