"""FastAPI application factory. `uvicorn sos.main:app` on the box; tests call create_app(settings, background=False)."""
from __future__ import annotations

import asyncio
import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sos import __version__, db, library, manifest, readiness, search as search_mod, sensors, system
from sos.config import Settings, get_settings
from sos.content import ContentCache
from sos.kiwix import KiwixClient
from sos.routers import ai, cards, household, kiosk, notes, pages, places, playbooks, search, status
from sos.routers import sensors as sensors_router
from sos.routers import situation as situation_router
from sos.routers import library as library_router
from sos.routers import map as map_router
from sos.routers import system as system_router

log = logging.getLogger(__name__)


def _bootstrap(settings: Settings) -> None:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    try:
        db.init_schema(conn)
        if settings.manifests.is_dir():
            library.upsert_items(conn, manifest.load_manifests(settings.manifests))
        if shutil.which(library.KIWIX_MANAGE):
            library.rescan(conn, settings)
        else:
            library.refresh_items(conn, settings)
    finally:
        conn.close()


def create_app(settings: Settings | None = None, background: bool = True) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _bootstrap(settings)
        app.state.settings = settings
        app.state.kiwix = KiwixClient(settings.kiwix_url)
        from sos.ai import LlamaClient
        from sos.ai_runtime import AiRuntime, restore_on_startup, shutdown as ai_shutdown
        app.state.conn = db.connect(settings.db_path)
        app.state.ai_runtime = AiRuntime(settings=settings, llama=LlamaClient(settings.llama_url))
        await restore_on_startup(app.state.ai_runtime, app.state.conn)
        app.state.tokens = system.TokenStore()
        app.state.pin_limiter = system.RateLimiter()
        app.state.content = ContentCache(settings.playbooks)
        app.state.updater = system.UpdateRunner()
        app.state.watchdog = system.ThermalWatchdog(settings, settings.db_path)
        app.state.watchdog.app = app
        app.state.idle = "active"
        app.state.backlight_level = 100
        tasks: list[asyncio.Task] = []
        if background:
            tasks.append(asyncio.create_task(app.state.watchdog.run()))
            tasks.append(asyncio.create_task(search_mod.warm(settings, app.state.kiwix, settings.db_path)))
            tasks.append(asyncio.create_task(readiness.nightly(settings, app.state.content, settings.db_path)))
            if settings.sensors:
                tasks.append(asyncio.create_task(sensors.run(settings, settings.db_path)))
        try:
            yield
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await ai_shutdown(app.state.ai_runtime)
            app.state.conn.close()
            await app.state.kiwix.aclose()

    app = FastAPI(title="Operation SOS", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    for router in (status.router, library_router.router, search.router, playbooks.router, cards.router, pages.router,
                   map_router.router, places.router, notes.router, ai.router, kiosk.router, system_router.router,
                   household.router, situation_router.router, sensors_router.router):
        app.include_router(router, prefix="/api")

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        parts = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request"})

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal error"})

    return app


app = create_app()
