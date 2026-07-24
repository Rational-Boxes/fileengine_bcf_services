"""BCF-XML codec + endpoints (Phase E / §11) — hermetic golden round-trips."""
import base64

from fastapi.testclient import TestClient

from bcf_service.app import build_app
from bcf_service.bcf_xml import (
    bcfv_to_viewpoint_json,
    export_bcfzip,
    import_bcfzip,
    markup_to_topic,
    topic_to_markup,
    viewpoint_json_to_bcfv,
)
from bcf_service.config import Config


# A viewpoint in BCF-API JSON form (as xeokit getViewpoint() emits): camera +
# section plane + selection + a visibility exception, with an IFC component.
VIEWPOINT = {
    "perspective_camera": {
        "camera_view_point": {"x": 1.0, "y": 2.0, "z": 3.0},
        "camera_direction": {"x": 0.0, "y": 0.0, "z": -1.0},
        "camera_up_vector": {"x": 0.0, "y": 1.0, "z": 0.0},
        "field_of_view": 60.0,
    },
    "clipping_planes": [
        {"location": {"x": 0.0, "y": 0.0, "z": 0.0}, "direction": {"x": 1.0, "y": 0.0, "z": 0.0}},
    ],
    "components": {
        "selection": [{"ifc_guid": "3xY7Uv$abc0000000000w1"}],
        "visibility": {"default_visibility": True, "exceptions": [{"ifc_guid": "2aB3Cd$xyz0000000000q9"}]},
    },
}

TOPIC = {
    "guid": "11111111-1111-4111-8111-111111111111",
    "title": "Clash: duct vs beam",
    "topic_type": "Clash",
    "topic_status": "Open",
    "priority": "High",
    "creation_date": "2026-07-23T10:00:00Z",
    "creation_author": "alice",
    "comments": [
        {"guid": "22222222-2222-4222-8222-222222222222", "date": "2026-07-23T10:01:00Z",
         "author": "alice", "comment": "The duct clashes with the beam here.",
         "viewpoint_guid": "33333333-3333-4333-8333-333333333333"},
    ],
    "viewpoints": [
        {"guid": "33333333-3333-4333-8333-333333333333", "viewpoint": VIEWPOINT, "snapshot": b"\x89PNG\r\n\x1a\nfake"},
    ],
}


def test_viewpoint_json_bcfv_roundtrip():
    xml = viewpoint_json_to_bcfv(VIEWPOINT, "vp-guid")
    back = bcfv_to_viewpoint_json(xml)
    pc = back["perspective_camera"]
    assert pc["camera_view_point"] == {"x": 1.0, "y": 2.0, "z": 3.0}
    assert pc["field_of_view"] == 60.0
    assert back["clipping_planes"][0]["direction"] == {"x": 1.0, "y": 0.0, "z": 0.0}
    assert back["components"]["selection"][0]["ifc_guid"] == "3xY7Uv$abc0000000000w1"
    assert back["components"]["visibility"]["default_visibility"] is True
    assert back["components"]["visibility"]["exceptions"][0]["ifc_guid"].endswith("q9")


def test_markup_roundtrip_preserves_guids_and_comments():
    xml = topic_to_markup(TOPIC)
    t = markup_to_topic(xml)
    assert t["guid"] == TOPIC["guid"]
    assert t["topic_type"] == "Clash" and t["topic_status"] == "Open"
    assert t["title"] == TOPIC["title"]
    assert len(t["comments"]) == 1
    assert t["comments"][0]["guid"] == TOPIC["comments"][0]["guid"]
    assert t["comments"][0]["viewpoint_guid"] == TOPIC["viewpoints"][0]["guid"]
    assert t["viewpoints"][0]["guid"] == TOPIC["viewpoints"][0]["guid"]


def test_bcfzip_roundtrip_end_to_end():
    archive = export_bcfzip([TOPIC])
    # A valid zip with the version marker + the topic folder.
    import zipfile
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert "bcf.version" in z.namelist()
        assert f"{TOPIC['guid']}/markup.bcf" in z.namelist()

    got = import_bcfzip(archive)
    assert len(got) == 1
    t = got[0]
    assert t["guid"] == TOPIC["guid"]
    assert t["comments"][0]["comment"].startswith("The duct clashes")
    v = t["viewpoints"][0]
    assert v["guid"] == TOPIC["viewpoints"][0]["guid"]
    assert v["snapshot"] == b"\x89PNG\r\n\x1a\nfake"  # snapshot bytes survive
    assert v["viewpoint"]["perspective_camera"]["field_of_view"] == 60.0  # viewpoint survives


def test_import_invalid_zip_raises():
    import pytest
    with pytest.raises(Exception):
        import_bcfzip(b"this is not a zip")


# --------------------------- endpoints ------------------------------------- #

def _client() -> TestClient:
    return TestClient(build_app(Config()))


def test_export_then_import_endpoints_roundtrip():
    c = _client()
    # Export: topics with a base64 snapshot → a .bcfzip download.
    payload = {
        "topics": [{
            **{k: v for k, v in TOPIC.items() if k != "viewpoints"},
            "viewpoints": [{
                "guid": TOPIC["viewpoints"][0]["guid"],
                "viewpoint": VIEWPOINT,
                "snapshot_b64": base64.b64encode(b"PNGDATA").decode("ascii"),
            }],
        }],
    }
    r = c.post("/bcf/2.1/bcf-xml/export", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    archive = r.content

    # Import the archive back → decoded topics (snapshot re-emitted as base64).
    r2 = c.post("/bcf/2.1/bcf-xml/import", content=archive)
    assert r2.status_code == 200
    body = r2.json()
    assert body["persisted"] is False
    t = body["topics"][0]
    assert t["guid"] == TOPIC["guid"]
    v = t["viewpoints"][0]
    assert base64.b64decode(v["snapshot_b64"]) == b"PNGDATA"
    assert v["viewpoint"]["clipping_planes"][0]["location"] == {"x": 0.0, "y": 0.0, "z": 0.0}


def test_export_unsupported_version_404():
    c = _client()
    assert c.post("/bcf/9.9/bcf-xml/export", json={"topics": []}).status_code == 404


def test_import_bad_archive_400():
    c = _client()
    assert c.post("/bcf/2.1/bcf-xml/import", content=b"garbage").status_code == 400
