from typing import Literal

from pydantic import Field

from operia.mobile_forensics.schemas import StrictModel


class AcquisitionMetadata(StrictModel):
    authorization: str = Field(min_length=10, max_length=4000)
    scope: str = Field(min_length=10, max_length=4000)
    provenance: str = Field(min_length=10, max_length=4000)
    acquisition_method: str = Field(min_length=3, max_length=160)
    acquisition_date_original: str = Field(min_length=3, max_length=80)
    retention_policy: str = Field(min_length=10, max_length=4000)
    restrictions: str = Field(min_length=3, max_length=4000)
    declared_os_version: str = Field(min_length=1, max_length=80)


class JobCreate(StrictModel):
    acquisition_id: int = Field(gt=0)
    indicator_set_id: int | None = Field(default=None, gt=0)
    demo_rules: bool = Field(default=False, strict=True)


class NativeReviewCreate(StrictModel):
    conclusion: Literal["inconcluso", "actividad_sospechosa", "indicios_compatibles_con_compromiso", "sin_indicios_en_el_alcance_examinado", "compromiso_confirmado_por_revision_profesional"]
    artifact_ids: list[str] = Field(max_length=100)
    rationale: str = Field(min_length=10, max_length=8000)
    alternatives: str = Field(min_length=10, max_length=4000)
    limitations: str = Field(min_length=10, max_length=4000)
    current_activity: str = Field(min_length=10, max_length=4000)
    chronology: str = Field(min_length=10, max_length=4000)
    attribution: str = Field(min_length=10, max_length=4000)
    coverage_justification: str = Field(min_length=10, max_length=4000)


class ExportCreate(StrictModel):
    format: Literal["json", "csv"] = "json"
