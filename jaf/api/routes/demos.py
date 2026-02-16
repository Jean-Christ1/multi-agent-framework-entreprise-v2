"""
JAF Demo API Routes
====================

Endpoints for listing and running demo scenarios.

- GET  /api/v1/demos          → list available demos
- POST /api/v1/demos/{id}/run → run a demo, returns process_id for SSE streaming
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import asyncio

from fastapi import APIRouter, HTTPException

from jaf.demos.registry import list_demos, run_demo, DEMO_SCENARIOS
from jaf.api.routes.stream import push_event, get_or_create_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demos", tags=["demos"])


@router.get("")
async def get_demos():
    """List all available demo scenarios."""
    return {"demos": list_demos()}


@router.post("/{demo_id}/run")
async def run_demo_endpoint(demo_id: str):
    """
    Run a demo scenario.

    Returns a process_id immediately. The client should connect
    to /api/v1/stream/{process_id} via SSE to receive real-time events.
    """
    if demo_id not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Demo '{demo_id}' not found. Available: {list(DEMO_SCENARIOS.keys())}",
        )

    scenario = DEMO_SCENARIOS[demo_id]

    # Pre-create the event queue so SSE can connect before events start
    import uuid
    process_id = str(uuid.uuid4())
    get_or_create_queue(process_id)

    async def _run():
        """Background task that runs the demo and pushes events."""
        async def event_callback(event: Dict[str, Any]):
            # Override process_id to match what we returned
            event["process_id"] = process_id
            await push_event(process_id, event)

        try:
            await run_demo(demo_id, event_callback=event_callback, process_id=process_id)
        except Exception as e:
            logger.exception(f"Demo {demo_id} failed: {e}")
            await push_event(process_id, {
                "process_id": process_id,
                "actionType": "error",
                "agentId": "engine",
                "status": "error",
                "message": f"Demo failed: {str(e)}",
                "data": {"error": str(e)},
            })

    # Use asyncio.create_task for true background execution
    # (FastAPI BackgroundTasks can delay the response with async functions)
    asyncio.create_task(_run())

    return {
        "process_id": process_id,
        "demo_id": demo_id,
        "demo_name": scenario["name"],
        "mode": scenario["mode"],
        "model": scenario.get("model"),
        "stream_url": f"/api/v1/stream/{process_id}",
    }
