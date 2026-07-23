"""BCF-API HTTP surface (buildingSMART BCF-API 2.1).

Scaffold status: the **discovery** endpoints — the minimum a BCF Manager hits
before authenticating — are implemented; the authenticated data endpoints
(projects / topics / comments / viewpoints, §12) return 501 until Phase F wires
the shared ``comment_store`` + BCF projection tables + OAuth verification.

Versioned under ``/bcf/{version}/…`` so a ``/bcf/3.0/`` OpenCDE Foundation tier
can layer on later (§12). ``GET /bcf/versions`` is unversioned.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import SUPPORTED_BCF_VERSIONS

router = APIRouter(prefix="/bcf")

# The data endpoints a BCF Manager exercises once authenticated — all pending the
# Phase F implementation. Listed here so the scaffold self-documents the surface.
_PENDING = "Not implemented in the scaffold — wired in Phase F (§12)."


def _check_version(version: str) -> None:
    if version not in SUPPORTED_BCF_VERSIONS:
        raise HTTPException(status_code=404, detail=f"Unsupported BCF version: {version}")


@router.get("/versions")
def versions() -> dict:
    """Advertise the BCF-API versions this server speaks (buildingSMART /versions)."""
    return {
        "versions": [
            {"version_id": v, "detailed_version": f"BCF-API {v}"} for v in SUPPORTED_BCF_VERSIONS
        ]
    }


@router.get("/{version}/auth")
def auth(version: str, request: Request) -> dict:
    """OAuth 2.0 discovery (buildingSMART /auth). Points desktop tools at the
    Phase 1.7 authorization server (ldap_manager). HTTP Basic is deliberately not
    offered — bearer/OAuth only."""
    _check_version(version)
    cfg = request.app.state.config
    return {
        "oauth2_auth_url": cfg.oauth_auth_url,
        "oauth2_token_url": cfg.oauth_token_url,
        "http_basic_supported": False,
        "supported_oauth2_flows": ["authorization_code_grant"],
    }


@router.get("/{version}/current-user")
def current_user(version: str) -> JSONResponse:
    """Identity of the bearer (buildingSMART /current-user). Pending OAuth wiring."""
    _check_version(version)
    return JSONResponse({"error": _PENDING}, status_code=501)


@router.get("/{version}/projects")
def list_projects(version: str) -> JSONResponse:
    """Projects the caller can see — each maps to a FileEngine folder (§10). Pending."""
    _check_version(version)
    return JSONResponse({"error": _PENDING}, status_code=501)
