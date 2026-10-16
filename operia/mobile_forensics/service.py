"""Bounded structural import. Never authenticates an externally declared MVT run."""
import hashlib
import json
import math
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.identity.dependencies import CurrentUser


def scoped_case(db: Session, case_id: int, user: CurrentUser) -> Case:
    case = db.get(Case, case_id)
    # Null tenancy is deliberately not a wildcard, including for administrators.
    if not user.organization_id or not case or case.organization_id != user.organization_id:
        raise HTTPException(404, "Caso no disponible en tu organización")
    return case


def scoped_exam(db, case_id, exam_id, user):
    from operia.mobile_forensics.models import MobileExam
    scoped_case(db, case_id, user)
    exam = db.get(MobileExam, exam_id)
    if not exam or exam.case_id != case_id or exam.organization_id != user.organization_id:
        raise HTTPException(404, "Examen no encontrado en este caso")
    return exam


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Claves JSON duplicadas")
        result[key] = value
    return result


def bounded_json(raw: bytes):
    # Scan depth before json.loads; bytes are already preserved unmodified in memory.
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > 32:
                raise HTTPException(422, "JSON supera profundidad máxima de 32")
        elif char in (93, 125):
            depth -= 1
    try:
        def invalid_constant(value):
            raise ValueError("Número JSON no finito")
        def finite_float(value):
            result = float(value)
            if not math.isfinite(result):
                raise ValueError("Número JSON fuera de rango")
            return result
        result = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_pairs,
                            parse_constant=invalid_constant, parse_float=finite_float)
        pending = [result]
        while pending:
            value = pending.pop()
            if isinstance(value, str):
                value.encode("utf-8")  # Reject escaped unpaired Unicode surrogates.
            elif isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(422, "JSON UTF-8 inválido, ambiguo o no finito")


def parse_result(raw: bytes, filename: str, platform: str):
    # Deliberately narrow pilot. Filename alone is insufficient; structural schema
    # must match too. There is no claim of authenticated provenance or full coverage.
    accepted = {"ios": {"safari_history", "sms"}, "android": {"sms"}}
    if not re.fullmatch(r"[a-z_]+\.json", filename):
        raise HTTPException(422, "Nombre inválido: no se aceptan rutas ni archivos comprimidos")
    module = filename[:-5]
    detected = module.endswith("_detected")
    base = module.removesuffix("_detected")
    if base not in accepted[platform]:
        raise HTTPException(422, "Formato no admitido por el piloto: sms o safari_history de iOS")
    records = bounded_json(raw)
    if not isinstance(records, list) or len(records) > 10000:
        raise HTTPException(422, "Se requiere una lista de hasta 10000 registros MVT")
    for record in records:
        if not isinstance(record, dict) or not record:
            raise HTTPException(422, "Registro MVT vacío o incompatible")
        if base == "safari_history":
            valid = isinstance(record.get("url"), str) and bool(record["url"].strip())
        else:
            valid = isinstance(record.get("body"), str) and any(
                key in record for key in ("address", "phone_number", "isodate", "date", "timestamp")
            )
        if not valid:
            raise HTTPException(422, "Campos del registro incompatibles con el módulo declarado")
    return records, len(records) if detected else 0


def public_exam(exam):
    return {key: getattr(exam, key) for key in (
        "id", "case_id", "device_id", "operator_id", "created_at", "authorization", "data_owner_consent", "scope",
        "provenance", "acquisition_method", "acquisition_date", "retention_policy",
        "declared_mvt_version", "declared_run_id", "indicators_description", "filename",
        "sha256", "record_count", "candidate_count", "coverage", "limitations"
    )} | {"technical_status": "importado", "forensic_conclusion": "requiere_revision",
         "engine_validation": "no_validado", "size_bytes": len(exam.original_bytes)}


def verify_original(exam):
    if digest(exam.original_bytes) != exam.sha256:
        raise HTTPException(409, "Integridad alterada: no se puede revisar ni exportar")
