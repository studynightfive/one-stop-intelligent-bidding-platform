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


def create_app() -> FastAPI:
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
    app.include_router(api_router, prefix="/api/v1")
    app.openapi = _load_contract  # type: ignore[method-assign]
    return app


app = create_app()
