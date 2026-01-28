"""Server-Sent Events (SSE) endpoint."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from vibecc.api.dependencies import get_event_manager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from vibecc.api.events import EventManager

EventManagerDep = Annotated["EventManager", Depends(get_event_manager)]

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    event_manager: EventManagerDep,
    project_id: str | None = Query(default=None, description="Filter by project ID"),
) -> StreamingResponse:
    """Subscribe to Server-Sent Events stream.

    Events are filtered by project_id if provided, otherwise all events are sent.
    A heartbeat is sent every 30 seconds to keep the connection alive.
    """
    em: EventManager = event_manager
    subscriber = em.subscribe(project_id)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    # Wait for event with timeout for heartbeat
                    event = await asyncio.wait_for(
                        subscriber.queue.get(),
                        timeout=em._heartbeat_interval,
                    )
                    yield event.to_sse()
                except TimeoutError:
                    # Send heartbeat on timeout
                    heartbeat = em.create_heartbeat_event()
                    yield heartbeat.to_sse()
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            em.unsubscribe(subscriber.id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
