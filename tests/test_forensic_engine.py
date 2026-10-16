import dataclasses
import json
import plistlib
from pathlib import Path

import pytest

from operia.forensic_engine.analysis import analyze, timeline_csv
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES, canonical_bytes, read_json, sha256
from operia.forensic_engine.contracts import EngineInputError, Source
from operia.forensic_engine.detection import normalize, validate_indicators
from operia.forensic_engine.readers import ProfilePlistReader, reader_order

FIXTURES = Path(__file__).parent / "fixtures" / "native_mobile"


def source(name="packages.txt", platform="android", format="android-pm-packages", raw=None):
    return Source("synthetic", name, platform, format, (FIXTURES / name).read_bytes() if raw is None else raw)


def test_original_ios_profile_xml_and_binary():
    original = source("profile.plist", "ios", "apple-profile-plist")
    output = analyze(original, demo=True)
    assert output["origin"] == "operia_native"
    assert output["artifacts"][0]["locator"] == "/PayloadContent/0"
    assert output["artifacts"][0]["normalized"]["profile_identifier"] == "invalid.operia.synthetic"
    assert output["source_manifest"][0]["sha256"] == sha256(original.raw)
    assert output["alerts"][0]["synthetic"] is True and not output["timeline"]
    binary = dataclasses.replace(original, raw=plistlib.dumps(plistlib.loads(original.raw), fmt=plistlib.FMT_BINARY))
    parsed = analyze(binary)
    assert len(parsed["artifacts"]) == 1 and not parsed["alerts"]
    assert "URL" not in parsed["artifacts"][0]["original"]  # Uninterpreted payload secrets are not copied.


def test_android_package_inventory_and_negative_demo():
    output = analyze(source(), demo=True)
    assert [item["normalized"]["package"] for item in output["artifacts"]] == ["invalid.operia.synthetic", "com.example.benign"]
    assert output["artifacts"][0]["normalized"]["path"] == "/data/app/synthetic/base.apk"
    assert len(output["alerts"]) == 1
    benign = analyze(source(raw=b"package:com.example.benign\n"), demo=True)
    assert benign["detection_status"] == "sin_coincidencias_en_reglas_aplicadas" and not benign["alerts"]
    no_rules = analyze(source())
    assert no_rules["detection_status"] == "sin_indicadores_ni_reglas_activas"
    assert no_rules["forensic_conclusion"] == "requiere_revision"


def test_log_epoch_timeline_reference_and_indicators():
    original = source("logcat-epoch.txt", "android", "android-logcat-epoch")
    output = analyze(original, (FIXTURES / "indicators.json").read_bytes())
    assert len(output["alerts"]) == 2
    assert [event["normalized_utc"] for event in output["timeline"]] == [
        "2023-11-14T22:13:20.000000Z", "2023-11-14T22:13:20.123000Z", "2023-11-14T22:13:21.999999Z"]
    assert output["artifacts"][0]["locator"] == "line:2"
    assert output["timeline"][0]["uncertainty"] == "reloj_no_contrastado"
    assert b"unix_epoch_seconds" in timeline_csv(output)
    assert canonical_bytes(output) == canonical_bytes(analyze(original, (FIXTURES / "indicators.json").read_bytes()))


@pytest.mark.parametrize("kind,value,expected", [
    ("domain", "ExAmPle.Invalid.", "example.invalid"),
    ("ip", "2001:0db8:0:0:0:0:0:1", "2001:db8::1"),
    ("url", "HTTPS://EXAMPLE.INVALID:443/Case?b=2&a=1#X", "https://example.invalid/Case?b=2&a=1#X"),
    ("package", "com.Example.App", "com.Example.App"),
    ("sha256", "A" * 64, "a" * 64),
])
def test_normalization_semantics(kind, value, expected):
    assert normalize(kind, value) == expected


@pytest.mark.parametrize("host,match,expected", [
    ("example.invalid", "exact", 1), ("sub.example.invalid", "exact", 0),
    ("sub.example.invalid", "subdomains", 1), ("badexample.invalid", "subdomains", 0),
    ("example.invalid.attacker.invalid", "subdomains", 0),
])
def test_domain_label_boundaries(host, match, expected):
    dataset = read_json((FIXTURES / "indicators.json").read_bytes())
    dataset["items"][0]["match"] = match
    output = analyze(source("logcat-epoch.txt", "android", "android-logcat-epoch",
        f"1700000000.000 1 2 I Test: https://{host}/\n".encode()), canonical_bytes(dataset))
    assert len(output["alerts"]) == expected


@pytest.mark.parametrize("raw,platform,format,status", [
    (b"", "android", "android-pm-packages", "sin_registros"),
    (b"garbage", "android", "android-pm-packages", "no_compatible"),
    (b"package:com.ok.app\nunsupported line\n", "android", "android-pm-packages", "analizado"),
    (b"\xff", "android", "android-logcat-epoch", "corrupto"),
    (b"10-16 17:00:00 1 2 I X: unknown year and zone", "android", "android-logcat-epoch", "no_compatible"),
    (b"PKencrypted archive", "ios", "apple-profile-plist", "no_compatible"),
    (b"<?xml broken", "ios", "apple-profile-plist", "corrupto"),
    (b"<?xml?><!ENTITY x SYSTEM 'file:///secret'>", "ios", "apple-profile-plist", "no_compatible"),
])
def test_missing_corrupt_ambiguous_and_unsupported(raw, platform, format, status):
    output = analyze(source(platform=platform, format=format, raw=raw))
    assert output["coverage"]["sources"][0]["status"] == status
    assert output["forensic_conclusion"] == "requiere_revision"
    if b"unknown year" in raw:
        assert not output["timeline"]


def test_profile_duplicates_hostile_depth_and_invalid_schema():
    root = plistlib.loads((FIXTURES / "profile.plist").read_bytes())
    root["PayloadContent"].append({"PayloadType": 10})
    output = analyze(source("profile.plist", "ios", "apple-profile-plist", plistlib.dumps(root)))
    assert len(output["artifacts"]) == 1 and len(output["coverage"]["sources"][0]["excluded"]) == 1
    raw = b'<plist version="1.0"><dict><key>x</key><string>1</string><key>x</key><string>2</string></dict></plist>'
    assert analyze(source("profile.plist", "ios", "apple-profile-plist", raw))["coverage"]["sources"][0]["status"] == "corrupto"
    for value in (b'{"x":1,"x":2}', b'{"x":NaN}', b'"\\ud800"', b'[' * 25 + b']' * 25):
        with pytest.raises(EngineInputError):
            read_json(value)


def test_indicators_reject_unsupported_patterns_and_commands():
    dataset = read_json((FIXTURES / "indicators.json").read_bytes())
    for key, value in (("match", "regex"), ("type", "stix"), ("type", "python")):
        item = {**dataset, "items": [{**dataset["items"][0], key: value}]}
        with pytest.raises(EngineInputError):
            validate_indicators(canonical_bytes(item))
    with pytest.raises(EngineInputError):
        normalize("url", "https://user:password@example.invalid/")
    with pytest.raises(EngineInputError):
        analyze(source(raw=b"x" * (MAX_SOURCE_BYTES + 1)))
    with pytest.raises(EngineInputError):
        analyze(dataclasses.replace(source(), filename="../escape.txt"))


def test_reader_registry_detects_duplicates_cycles_and_missing_dependencies():
    class Copy(ProfilePlistReader):
        pass
    with pytest.raises(EngineInputError, match="duplicada"):
        reader_order([Copy(), Copy()])
    class Circular(ProfilePlistReader):
        dependencies = (ProfilePlistReader.identifier,)
    with pytest.raises(EngineInputError, match="circular"):
        reader_order([Circular()])
    class Missing(ProfilePlistReader):
        dependencies = ("not-installed",)
    with pytest.raises(EngineInputError, match="ausente"):
        reader_order([Missing()])


def test_duplicate_records_are_not_independent_alerts():
    original = source(raw=b"package:invalid.operia.synthetic\npackage:invalid.operia.synthetic\n")
    output = analyze(original, demo=True)
    assert len(output["artifacts"]) == 2 and len(output["alerts"]) == 1
    assert output["artifacts"][1]["duplicate_of"] == output["artifacts"][0]["id"]
    assert output["correlations"][0]["type"] == "duplicate_record"


@pytest.mark.parametrize("kind,value,filename,platform,format,expected", [
    ("sha256", "fixture_hash", "packages.txt", "android", "android-pm-packages", 1),
    ("package", "invalid.operia.synthetic", "packages.txt", "android", "android-pm-packages", 1),
    ("package", "invalid.operia.SYNTHETIC", "packages.txt", "android", "android-pm-packages", 0),
    ("path", "/data/app/synthetic/base.apk", "packages.txt", "android", "android-pm-packages", 1),
    ("profile_identifier", "invalid.operia.synthetic", "profile.plist", "ios", "apple-profile-plist", 1),
    ("url", "HTTPS://EXAMPLE.INVALID:443/path", "logcat-epoch.txt", "android", "android-logcat-epoch", 1),
    ("url", "https://example.invalid/Path", "logcat-epoch.txt", "android", "android-logcat-epoch", 0),
])
def test_supported_comparators_and_hash_observation_scope(kind, value, filename, platform, format, expected):
    original = source(filename, platform, format)
    dataset = read_json((FIXTURES / "indicators.json").read_bytes())
    dataset["items"] = [{"id": "test", "type": kind, "value": sha256(original.raw) if value == "fixture_hash" else value, "match": "exact"}]
    result = analyze(original, canonical_bytes(dataset))
    assert len(result["alerts"]) == expected
    if kind == "sha256":
        assert len(result["alerts"][0]["artifact_ids"]) == 2


def test_ipv6_comparator_uses_canonical_url_host():
    original = source("logcat-epoch.txt", "android", "android-logcat-epoch",
        b"1700000000.000 1 2 I Test: https://[2001:db8::1]/\n")
    dataset = read_json((FIXTURES / "indicators.json").read_bytes())
    dataset["items"] = [{"id": "ipv6", "type": "ip", "value": "2001:0db8:0:0:0:0:0:1", "match": "exact"}]
    assert len(analyze(original, canonical_bytes(dataset))["alerts"]) == 1


def test_empty_indicator_set_cannot_claim_applied_detection():
    dataset = read_json((FIXTURES / "indicators.json").read_bytes())
    dataset["items"] = []
    with pytest.raises(EngineInputError):
        analyze(source(), canonical_bytes(dataset))
