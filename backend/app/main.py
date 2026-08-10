"""L0 独占的 FastAPI 应用装配入口。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors.handlers import register_exception_handlers
from app.domains.evaluations.container import M6Container, build_m6_container_with_m4
from app.domains.evaluations.ports import AuthPrincipal, RecordingPorts
from app.domains.evaluations.router import auth_principal_from_context, get_actor, get_container
from app.domains.evaluations.store import EvaluationStore
from app.models_registry import register_models


def _contract_path() -> Path:
    configured = os.getenv("OPENAPI_CONTRACT_PATH")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"


@lru_cache(maxsize=1)
def _load_contract() -> dict[str, Any]:
    path = _contract_path()
    if not path.is_file():
        raise RuntimeError(f"OpenAPI contract not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    if not isinstance(contract, dict) or contract.get("openapi") != "3.1.0":
        raise RuntimeError("OpenAPI contract must be a valid 3.1.0 document")
    return contract


def _configure_m6_dependencies(app: FastAPI) -> None:
    """Bridge M6 to M4 authentication and shared platform services."""
    store = EvaluationStore()
    bid_snapshot = RecordingPorts()

    async def provide_container(db: DBSession) -> M6Container:
        return build_m6_container_with_m4(db, bid_snapshot=bid_snapshot, store=store)

    async def provide_actor(current_user: AuthenticatedUser) -> AuthPrincipal:
        return auth_principal_from_context(current_user)

    app.state.m6_store = store
    app.state.m6_bid_snapshot = bid_snapshot
    app.dependency_overrides[get_container] = provide_container
    app.dependency_overrides[get_actor] = provide_actor


def create_app() -> FastAPI:
    register_models()
    app = FastAPI(
        title="一站式智能招投标平台 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
    )
    origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://127.0.0.1:3210").split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "Idempotency-Key", "If-Match"],
    )
    register_exception_handlers(app)
    _configure_m6_dependencies(app)
    app.include_router(api_router, prefix="/api/v1")
    app.openapi = _load_contract  # type: ignore[method-assign]
    return app


app = create_app()
