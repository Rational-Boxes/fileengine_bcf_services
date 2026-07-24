"""FastAPI application factory for the BCF-API subservice.

``build_app`` stays pure (no .env side effects) so tests are hermetic; ``create_app``
loads ``./.env`` first for real launches. The HTTP surface is two routers:
``monitoring`` (loopback health) and ``bcf_api`` (the BCF-API discovery surface;
data endpoints land in Phase F).
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import __version__
from .bcf_api import router as bcf_router
from .bcf_xml_api import router as bcf_xml_router
from .config import Config
from .monitoring import MONITORING_PATHS, router as monitoring_router

log = logging.getLogger("bcf_service.app")


def build_app(config: Config | None = None) -> FastAPI:
    config = config or Config()
    app = FastAPI(title="bcf_service", version=__version__)
    app.state.config = config

    # Route-scoped IP allowlist for the unauthenticated monitoring endpoints. They
    # already bind loopback; when FILEENGINE_MONITORING_ALLOW_IPS is set
    # (comma-separated client IPs), a monitoring request from a non-listed address
    # is refused with 403 — matching the discussion / bridge convention.
    monitor_allow = {ip.strip() for ip in
                     os.environ.get("FILEENGINE_MONITORING_ALLOW_IPS", "").split(",") if ip.strip()}

    @app.middleware("http")
    async def _guard_monitoring(request, call_next):
        if monitor_allow and request.url.path in MONITORING_PATHS:
            client = request.client.host if request.client else ""
            if client not in monitor_allow:
                return JSONResponse({"error": "forbidden"}, status_code=403)
        return await call_next(request)

    # Browser CORS for a SPA on another origin (off unless configured; never "*").
    if config.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(monitoring_router)
    app.include_router(bcf_router)
    app.include_router(bcf_xml_router)
    return app


def create_app() -> FastAPI:
    """ASGI factory that loads ``./.env`` then builds the app — for launching via
    ``uvicorn bcf_service.app:create_app --factory`` or the ``bcf-service`` script."""
    from .config import load_dotenv
    load_dotenv()
    return build_app(Config())


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    app = create_app()
    cfg = app.state.config
    log.info("bcf_service %s — http=%s:%s core=%s", __version__, cfg.http_host, cfg.http_port,
             cfg.grpc_address)
    uvicorn.run(app, host=cfg.http_host, port=cfg.http_port)


if __name__ == "__main__":
    main()
