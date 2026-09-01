import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_research_session_service
from app.models.message import Message
from app.models.report import Report
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.session import MessageRead, ReportRead, SessionCreate, SessionRead
from app.services.exceptions import ProjectNotFoundError, ResearchSessionNotFoundError
from app.services.research_session_service import ResearchSessionService
from app.workers.celery_app import celery_app

router = APIRouter()


@router.post(
    "/projects/{project_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    project_id: uuid.UUID,
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSession:
    try:
        research_session = await service.create_session(project_id, current_user.id, body.query)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc

    # Enqueued by task name (not by importing app.workers.tasks) so the API
    # process never has to import the ai/ graph machinery just to hand off a
    # session id — see app/core/container.py's docstring on keeping the API
    # and worker processes' import graphs independent.
    celery_app.send_task("research.run_pipeline", args=[str(research_session.id)])
    return research_session


@router.get("/projects/{project_id}/sessions", response_model=list[SessionRead])
async def list_sessions(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResearchSessionService = Depends(get_research_session_service),
) -> list[ResearchSession]:
    try:
        return await service.list_sessions(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc


@router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSession:
    try:
        return await service.get_session(session_id, current_user.id)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found"
        ) from exc


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def list_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResearchSessionService = Depends(get_research_session_service),
) -> list[Message]:
    try:
        return await service.list_messages(session_id, current_user.id)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found"
        ) from exc


@router.get("/sessions/{session_id}/report", response_model=ReportRead)
async def get_session_report(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResearchSessionService = Depends(get_research_session_service),
) -> Report:
    try:
        report = await service.get_latest_report(session_id, current_user.id)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found"
        ) from exc
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report
