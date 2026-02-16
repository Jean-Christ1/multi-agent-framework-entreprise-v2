"""
JAF SSE Stream Endpoint
========================

Server-Sent Events endpoint for real-time process monitoring.
The frontend connects via EventSource and receives typed events
as the NativeAdapter executes tools and reasons about the goal.

Events follow the format:
    data: {"actionType": "tool_called", "agentId": "...", "message": "...", ...}
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["stream"])

# In-memory event queues per process_id.
# When a process runs, it pushes events here; the SSE endpoint drains them.
_event_queues: dict[str, asyncio.Queue] = {}


def get_or_create_queue(process_id: str) -> asyncio.Queue:
    """Get (or create) an event queue for a process."""
    if process_id not in _event_queues:
        _event_queues[process_id] = asyncio.Queue()
    return _event_queues[process_id]


def cleanup_queue(process_id: str) -> None:
    """Remove event queue after process completes."""
    _event_queues.pop(process_id, None)


async def push_event(process_id: str, event: dict) -> None:
    """Push an event into the queue for a given process."""
    q = get_or_create_queue(process_id)
    await q.put(event)


async def _event_generator(process_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events from the process queue."""
    q = get_or_create_queue(process_id)

    while True:
        try:
            event = await asyncio.wait_for(q.get(), timeout=30.0)
        except asyncio.TimeoutError:
            # Send keepalive
            yield ": keepalive\n\n"
            continue

        event_type = event.get("actionType", "unknown")
        data = json.dumps(event, default=str)
        yield f"event: {event_type}\ndata: {data}\n\n"

        # If terminal event, close the stream
        if event_type in ("completed", "error"):
            break

    # Small delay so the client receives the final event before close
    await asyncio.sleep(0.1)
    cleanup_queue(process_id)


@router.get("/stream/{process_id}")
async def stream_events(process_id: str):
    """
    SSE endpoint for real-time process events.

    Usage from browser:
        const es = new EventSource('/api/v1/stream/<process_id>');
        es.addEventListener('tool_called', (e) => { ... });
    """
    return StreamingResponse(
        _event_generator(process_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
