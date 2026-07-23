# FileEngine BCF-API subservice

The **BCF (BIM Collaboration Format) protocol door** for FileEngine — a
Python/FastAPI service that lets external AEC tools (Revit, Navisworks, Solibri,
BIMcollab) collaborate live against FileEngine over **BCF-API 2.1**.

It implements Phase F / §12 of `frontend/design_documents/XEOKIT_UPGRADE_MARKUP_BCF_PLAN.md`.
It is **not** a second issue store: topics and comments live in the discussion
substrate (reached through the shared `comment_store` interface); this service owns
only the BCF *projection* tables (`bcf_project`, `bcf_topic`, `bcf_viewpoint`,
`bcf_guid_map`) in the same per-tenant schema. "Many doors, one core."

## Status — scaffold

Implemented:
- App factory + config (env-driven, `FILEENGINE_*` shared names, `BCF_*` knobs).
- Loopback health endpoints (`/healthz`, `/readyz`) with the monitoring IP allowlist.
- BCF-API **discovery**: `GET /bcf/versions`, `GET /bcf/{v}/auth` (OAuth 2.0 discovery
  pointing at ldap_manager / Phase 1.7), version guard.
- The per-tenant BCF projection **DDL** (`store.tenant_ddl`).

Pending (Phase F):
- Authenticated data endpoints: projects / topics / comments / viewpoints.
- Extraction of the shared `comment_store` interface from the discussion service so
  BCF writes go through one guarded path (ACL, FTS, mentions, event emission).
- OAuth2/JWKS bearer verification; live connection + CRUD adapter; BCF-XML round-trip
  handoff (Phase E) → live API (this service).

## Run

```bash
pip install -e .[dev]
cp .env.example .env         # fill FILEENGINE_JWT_SECRET etc.
bcf-service                  # uvicorn on 127.0.0.1:8098
# or: uvicorn bcf_service.app:create_app --factory --port 8098
```

## Test

```bash
pip install -e .[dev]
pytest                       # hermetic — no DB/core/LDAP needed
```
