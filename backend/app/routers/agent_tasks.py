"""Agent tasks router — view and manage autonomous agent results."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agent_task import AgentTask, AgentTaskStatus, AgentTaskType
from app.services.agent_service import create_agent_task

router = APIRouter(prefix="/api/agent-tasks", tags=["agent-tasks"])


def _task_response(task: AgentTask) -> dict:
    return {
        "id": str(task.id),
        "source_item_id": str(task.source_item_id) if task.source_item_id else None,
        "task_type": task.task_type.value,
        "prompt": task.prompt,
        "status": task.status.value,
        "steps": task.steps,
        "result_summary": task.result_summary,
        "result_items": task.result_items,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("")
async def list_agent_tasks(
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """List agent tasks, optionally filtered by status."""
    stmt = select(AgentTask).order_by(AgentTask.created_at.desc())

    if status:
        stmt = stmt.where(AgentTask.status == AgentTaskStatus(status))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return {
        "tasks": [_task_response(t) for t in tasks],
        "total": total,
    }


@router.get("/{task_id}")
async def get_agent_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Get detailed agent task result."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return _task_response(task)


@router.post("", status_code=201)
async def create_task(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Manually create an agent task."""
    prompt = body.get("prompt")
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt is required")

    task_type_str = body.get("task_type", "custom")
    try:
        task_type = AgentTaskType(task_type_str)
    except ValueError:
        task_type = AgentTaskType.custom

    source_item_id = None
    if body.get("source_item_id"):
        source_item_id = UUID(body["source_item_id"])

    task = await create_agent_task(db, source_item_id, prompt, task_type)
    return _task_response(task)


@router.post("/{task_id}/cancel", status_code=200)
async def cancel_agent_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Cancel a pending or running agent task."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if task.status not in (AgentTaskStatus.pending, AgentTaskStatus.running):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    task.status = AgentTaskStatus.cancelled
    await db.commit()
    return _task_response(task)
