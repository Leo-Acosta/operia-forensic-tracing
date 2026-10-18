"""Closed, passive interchange contract. Nothing in a report is executable."""
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_REPORT_BYTES = 262144
MAX_IMPORTS_PER_ORGANIZATION = 1000

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    @field_validator('*')
    @classmethod
    def valid_text(cls, value):
        if isinstance(value, str):
            try:
                value.encode('utf-8')
            except UnicodeError as error:
                raise ValueError('Texto Unicode inválido') from error
            if any(ord(char) < 32 and char not in '\t\r\n' for char in value):
                raise ValueError('Carácter de control inválido')
        return value

class Observation(StrictModel):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    member: str = Field(min_length=1, max_length=240)
    offset: int = Field(ge=0, le=1073741824)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator('member')
    @classmethod
    def safe_member(cls, value):
        if value.startswith(('/', '\\')) or '\\' in value or ':' in value or any(p in ('', '.', '..') for p in value.split('/')) or any(ord(c) < 32 for c in value):
            raise ValueError('Localizador relativo inválido')
        return value

class StaticReport(StrictModel):
    schema_version: Literal['operia-static-report/1']
    sample_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    provider: str = Field(pattern=r'^[A-Za-z0-9._-]{1,80}$')
    provider_version: str = Field(min_length=1, max_length=120)
    provider_revision: str = Field(min_length=1, max_length=120)
    operation: Literal['static-observations']
    coverage: Literal['empty', 'partial', 'complete']
    limitations: str = Field(min_length=1, max_length=4000)
    observations: list[Observation] = Field(max_length=200)

    @model_validator(mode='after')
    def consistent(self):
        ids = [o.id for o in self.observations]
        if len(ids) != len(set(ids)) or (self.coverage == 'empty') != (len(ids) == 0):
            raise ValueError('Cobertura o identificadores inconsistentes')
        return self

def parse_report(raw: bytes) -> StaticReport:
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('Informe excede el límite')
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('Clave duplicada')
            result[key] = value
        return result
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Constante inválida')))
        return StaticReport.model_validate(data)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('JSON inválido') from error

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def normalized(report):
    return json.dumps(report.model_dump(), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
