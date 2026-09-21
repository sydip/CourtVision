from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.application import router as application_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.data_status import router as data_status_router
from app.api.routes.health import router as health_router
from app.api.routes.playoffs import router as playoffs_router
from app.api.routes.predictions import router as predictions_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="CourtVision API",
        version="0.1.0",
        description="Local development API foundation for CourtVision.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(health_router, prefix="/api")
    app.include_router(data_status_router, prefix="/api")
    app.include_router(application_router, prefix="/api")
    app.include_router(playoffs_router, prefix="/api")
    app.include_router(predictions_router, prefix="/api")
    app.include_router(assistant_router, prefix="/api")
    return app


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        raise exc
    headers = exc.headers
    detail: Any = exc.detail
    content: dict[str, Any]
    if isinstance(detail, dict) and "error" in detail:
        content = detail
    else:
        content = {
            "error": {
                "code": str(exc.status_code),
                "message": str(detail),
            }
        }
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
            },
            "details": exc.errors(),
        },
    )


app = create_app()
