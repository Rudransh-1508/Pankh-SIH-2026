from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

import yaml

SOURCES_FILE = Path(__file__).resolve().parent / "data" / "sources.yaml"


@dataclass(frozen=True)
class Source:
    """An official Guideline document published by the ministry."""

    id: str
    title: str
    url: str
    sha256: str
    pages: int
    issued: date | None = None
    effective: date | None = None
    scanned: bool = False


@dataclass(frozen=True)
class Citation:
    """Where in an official Source a Rule or benefit comes from."""

    source_id: str
    page: int
    clause: str

    @property
    def source(self) -> Source:
        return sources()[self.source_id]

    @property
    def url(self) -> str:
        """Link that opens the PDF at the cited page."""
        return f"{self.source.url}#page={self.page}"


@cache
def sources() -> dict[str, Source]:
    raw = yaml.safe_load(SOURCES_FILE.read_text())
    return {source_id: Source(id=source_id, **fields) for source_id, fields in raw.items()}


def cite(source_id: str, page: int, clause: str) -> Citation:
    source = sources()[source_id]
    if not 1 <= page <= source.pages:
        raise ValueError(f"{source_id} has {source.pages} pages; page {page} does not exist")
    return Citation(source_id, page, clause)
