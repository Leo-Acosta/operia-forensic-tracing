import hashlib
import json
import math

from operia.forensic_engine.contracts import EngineInputError

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 5000
MAX_OUTPUT_BYTES = 16 * 1024 * 1024


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def checked_tree(value, depth=0, budget=None):
    if budget is None:
        budget = [50000]
    budget[0] -= 1
    if depth > 24 or budget[0] < 0:
        raise EngineInputError("Estructura supera profundidad o cantidad de nodos admitida")
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, float) and not math.isfinite(value):
        raise EngineInputError("Número no finito")
    elif isinstance(value, dict):
        for key, child in value.items():
            checked_tree(key, depth + 1, budget)
            checked_tree(child, depth + 1, budget)
    elif isinstance(value, (list, tuple)):
        for child in value:
            checked_tree(child, depth + 1, budget)


def read_json(raw: bytes, limit=MAX_SOURCE_BYTES):
    if len(raw) > limit:
        raise EngineInputError("JSON supera el límite de bytes")
    # Bound nesting before invoking the JSON decoder.
    quoted = escaped = False
    depth = 0
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 24:
                raise EngineInputError("JSON demasiado profundo")
        elif byte in (93, 125):
            depth -= 1

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise EngineInputError("Clave duplicada")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs)
        checked_tree(value, budget=[1000000])
        return value
    except (ValueError, UnicodeError, RecursionError) as error:
        raise EngineInputError("JSON inválido, ambiguo o fuera de límites") from error
