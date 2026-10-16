from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="after")
    @classmethod
    def nonblank(cls, value):
        if isinstance(value, str) and not value:
            raise ValueError("El campo no puede estar vacío")
        return value


class DeviceCreate(StrictModel):
    label: str = Field(min_length=1, max_length=160)
    platform: Literal["ios", "android"]
    identifier: str = Field(default="no registrado", max_length=160)


class ImportMetadata(StrictModel):
    authorization: str = Field(min_length=10, max_length=4000)
    data_owner_consent: Literal[True]
    scope: str = Field(min_length=10, max_length=4000)
    provenance: str = Field(min_length=10, max_length=4000)
    acquisition_method: str = Field(min_length=3, max_length=160)
    acquisition_date: str = Field(min_length=3, max_length=80)
    retention_policy: str = Field(min_length=10, max_length=4000)
    declared_mvt_version: str = Field(min_length=1, max_length=80)
    declared_run_id: str = Field(min_length=1, max_length=160)
    indicators_description: str = Field(min_length=3, max_length=4000)


class ReviewCreate(StrictModel):
    conclusion: Literal["inconcluso", "actividad_sospechosa", "indicios_compatibles_con_compromiso"]
    rationale: str = Field(min_length=10, max_length=8000)
    alternatives: str = Field(min_length=10, max_length=4000)
    limitations: str = Field(min_length=10, max_length=4000)
    record_indexes: list[int] = Field(max_length=100)
    current_activity: str = Field(min_length=10, max_length=4000)
    chronology: str = Field(min_length=10, max_length=4000)
    attribution: str = Field(min_length=10, max_length=4000)
