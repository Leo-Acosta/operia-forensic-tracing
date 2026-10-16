from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Source:
    id: str
    filename: str
    platform: str
    format: str
    raw: bytes


@dataclass
class ReadResult:
    status: str
    records: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)


class Reader(Protocol):
    identifier: str
    version: str
    platform: str
    format: str
    dependencies: tuple[str, ...]

    def read(self, source: Source) -> ReadResult: ...


class EngineInputError(ValueError):
    """A bounded input or explicit configuration is invalid."""
