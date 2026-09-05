# api/sos/routers/ai.py
"""AI endpoints: POST /ai/ask (Server-Sent Events), GET /ai/status, POST /ai/enable, POST /ai/disable."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sos.ai import MAX_QUESTION_CHARS, LlamaError, answer_events
from sos.ai_runtime import AiRuntime, disable_ai, enable_ai
from sos.routers import require_pin
from sos.db import get_setting
from fastapi import HTTPException

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

PING_INTERVAL_S = 10.0
TOTAL_TIMEOUT_S = 180.0
PING = ": ping\n\n"
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=4)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _runtime(request: Request) -> AiRuntime:
    return request.app.state.ai_runtime


@router.post("/ask")
async def ask(body: AskRequest, request: Request) -> StreamingResponse:
    rt = _runtime(request)
    state = request.app.state
    history = [m.model_dump() for m in body.history]

    async def stream():
        if rt.state != "ready":
            yield sse("error", {"code": "unavailable", "message": "The assistant is off. Turn it on in System."})
            return
        if rt.lock.locked():
            yield sse("error", {"code": "busy", "message": "Another question is being answered. Try again shortly.",
                                "retry_after": rt.retry_after()})
            return
        async with rt.lock:
            rt.busy_since = time.monotonic()
            queue: asyncio.Queue = asyncio.Queue()

            async def produce() -> None:
                try:
                    async with asyncio.timeout(TOTAL_TIMEOUT_S):
                        async for name, data in answer_events(body.question, history, state.conn, state.kiwix,
                                                              rt.llama, state.settings):
                            await queue.put((name, data))
                except TimeoutError:
                    await queue.put(("error", {"code": "timeout",
                                               "message": f"No answer within {int(TOTAL_TIMEOUT_S)} seconds."}))
                except LlamaError as exc:
                    await queue.put(("error", {"code": "unavailable", "message": str(exc)}))
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("ai: ask failed")
                    await queue.put(("error", {"code": "internal", "message": "The assistant hit an internal error."}))
                finally:
                    queue.put_nowait(None)

            task = asyncio.create_task(produce())
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), PING_INTERVAL_S)
                    except TimeoutError:
                        yield PING
                        continue
                    if item is None:
                        break
                    yield sse(item[0], item[1])
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                rt.busy_since = None

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/status")
async def status(request: Request) -> dict:
    return _runtime(request).snapshot()


@router.post("/enable", dependencies=[Depends(require_pin)])
async def enable(request: Request) -> dict:
    if get_setting(request.app.state.conn, "power_mode", "normal") == "low":
        raise HTTPException(status_code=409, detail="Leave low power mode to use the AI")
    snap = await enable_ai(_runtime(request), request.app.state.conn)
    return {"state": snap["state"]}


@router.post("/disable", dependencies=[Depends(require_pin)])
async def disable(request: Request) -> dict:
    snap = await disable_ai(_runtime(request), request.app.state.conn, "user")
    return {"state": snap["state"]}
