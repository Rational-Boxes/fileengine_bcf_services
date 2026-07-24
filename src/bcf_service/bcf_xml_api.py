# Copyright (C) 2026 James Hickman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""BCF-XML import/export endpoints (Phase E / §11).

Thin HTTP wrappers over the ``bcf_xml`` codec:

- ``POST /bcf/{version}/bcf-xml/export`` — body ``{"topics": [...]}`` (issue dicts;
  viewpoint snapshots as base64) → a ``.bcfzip`` download.
- ``POST /bcf/{version}/bcf-xml/import`` — a ``.bcfzip`` body → the decoded topics
  as JSON (snapshots re-emitted as base64). This is decode-only; **persisting**
  imported topics (upsert-by-guid into the discussion substrate + BCF projection)
  is Phase F, where the shared ``comment_store`` lands.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from .bcf_xml import export_bcfzip, import_bcfzip
from .config import SUPPORTED_BCF_VERSIONS

router = APIRouter(prefix="/bcf")


def _check_version(version: str) -> None:
    if version not in SUPPORTED_BCF_VERSIONS:
        raise HTTPException(status_code=404, detail=f"Unsupported BCF version: {version}")


@router.post("/{version}/bcf-xml/export")
async def bcf_xml_export(version: str, request: Request) -> Response:
    _check_version(version)
    body = await request.json()
    topics = body.get("topics") or []
    # Snapshots arrive base64-encoded in JSON; decode to bytes for the archive.
    for t in topics:
        for v in t.get("viewpoints") or []:
            b64 = v.pop("snapshot_b64", None)
            v["snapshot"] = base64.b64decode(b64) if b64 else None
    archive = export_bcfzip(topics, version=version)
    return Response(
        content=archive,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="issues.bcfzip"'},
    )


@router.post("/{version}/bcf-xml/import")
async def bcf_xml_import(version: str, request: Request) -> JSONResponse:
    _check_version(version)
    data = await request.body()
    try:
        topics = import_bcfzip(data)
    except Exception:
        return JSONResponse({"error": "Not a valid .bcfzip archive"}, status_code=400)
    # Re-emit snapshot bytes as base64 so the decode preview is JSON-serializable.
    for t in topics:
        for v in t.get("viewpoints") or []:
            snap = v.pop("snapshot", None)
            v["snapshot_b64"] = base64.b64encode(snap).decode("ascii") if snap else None
    return JSONResponse({"topics": topics, "persisted": False})  # persistence is Phase F
