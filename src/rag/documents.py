"""Load FEMS guideline documents from disk and split them into retrieval chunks.

Supports .md / .txt / .pdf so the user can drop public PDFs into the same
folder as the synthetic markdown and have them indexed together.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".md", ".txt", ".pdf"}


@dataclass
class Chunk:
    doc_id: str  # source filename stem
    chunk_id: str  # "<doc_id>::<n>" — unique, stable across rebuilds
    text: str
    source: str  # filename with extension


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def _split_long(text: str, target_chars: int, overlap: int) -> list[str]:
    """Hard-window a single oversized unit into target-sized slices with overlap."""
    step = max(1, target_chars - overlap)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + target_chars])
        if start + target_chars >= len(text):
            break
        start += step
    return pieces


def chunk_text(text: str, target_chars: int = 800, overlap: int = 150) -> list[str]:
    """Group paragraphs into chunks no larger than ~target_chars.

    Splits on blank lines so chunks stay on paragraph boundaries. A single
    paragraph longer than target_chars is hard-split into overlapping windows
    (the only place overlap is applied — overlap there preserves context across
    a forced mid-paragraph cut; paragraph-boundary cuts need no overlap).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units: list[str] = []
    for para in paragraphs:
        if len(para) > target_chars:
            units.extend(_split_long(para, target_chars, overlap))
        else:
            units.append(para)

    chunks: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(unit) + 2 > target_chars:
            chunks.append(current)
            current = unit
        else:
            current = f"{current}\n\n{unit}" if current else unit
    if current:
        chunks.append(current)
    return chunks


def load_documents(docs_dir: str | Path) -> list[Chunk]:
    """Read every supported file under docs_dir and return its chunks."""
    docs_dir = Path(docs_dir)
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        try:
            text = _read_file(path)
        except Exception as e:  # noqa: BLE001 - skip one bad file, keep indexing the rest
            print(f"[documents] skipped {path.name}: {e}")
            continue
        for i, piece in enumerate(chunk_text(text)):
            chunks.append(
                Chunk(
                    doc_id=path.stem,
                    chunk_id=f"{path.stem}::{i}",
                    text=piece,
                    source=path.name,
                )
            )
    return chunks
