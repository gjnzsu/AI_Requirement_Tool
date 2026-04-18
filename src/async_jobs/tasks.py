"""Celery tasks for async job execution."""

from __future__ import annotations

from typing import Dict, List

from src.async_jobs.celery_app import celery_app


@celery_app.task(name="src.async_jobs.process_coze_job")
def process_coze_job(
    *,
    user_input: str,
    conversation_id: str,
    conversation_history: List[Dict[str, str]],
    agent_mode: str,
):
    """Execute a Coze turn through a worker-local execution wrapper."""
    from src.services.async_coze_execution_service import (
        build_default_async_coze_execution_service,
    )

    execution_service = build_default_async_coze_execution_service()
    return execution_service.execute(
        user_input=user_input,
        conversation_id=conversation_id,
        conversation_history=conversation_history,
        agent_mode=agent_mode,
    )
