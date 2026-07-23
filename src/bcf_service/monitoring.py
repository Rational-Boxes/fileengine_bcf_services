"""Unauthenticated liveness/readiness endpoints.

Per the workspace monitoring convention these MUST bind loopback-only (the app's
default ``BCF_HTTP_HOST=127.0.0.1``); ``build_app`` additionally applies a
route-scoped IP allowlist (``FILEENGINE_MONITORING_ALLOW_IPS``) so they can never
be reached from a non-listed address even if the bind is widened.
"""
from __future__ import annotations

from fastapi import APIRouter

from . import __version__

router = APIRouter()

# Paths the allowlist middleware guards (see app.build_app).
MONITORING_PATHS = frozenset({"/healthz", "/readyz"})


@router.get("/healthz")
def healthz() -> dict:
    """Liveness — the process is up. No dependency checks."""
    return {"status": "ok", "service": "bcf_service", "version": __version__}


@router.get("/readyz")
def readyz() -> dict:
    """Readiness. Real dependency probes (Postgres, gRPC core, ldap_manager OAuth)
    are wired in Phase F; the scaffold reports ready so the process participates in
    orchestration without pretending to have verified downstreams."""
    return {"status": "ok", "checks": {"config": "ok"}}
