from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import authorize_project_module
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.documents import DocumentCategory, ImportTarget
from app.schemas.documents import (
    DocumentRead,
    DocumentUpdate,
    ExportDataset,
    ImportConfirmRead,
    ImportPreviewRead,
    KnowledgeQuery,
    KnowledgeQueryRead,
    ReportRead,
    ReportType,
)
from app.services.audit import AuditService
from app.services.authorization import Capability
from app.services.data_portability import ExportService, ImportService, ReportingService
from app.services.documents import DocumentService
from app.services.projects import ProjectService

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["documents-and-reports"],
    dependencies=[
        Depends(
            authorize_project_module(
                Capability.DOCUMENTS_READ,
                Capability.DOCUMENTS_MANAGE,
                path_overrides={"/knowledge/query": Capability.DOCUMENTS_READ},
            )
        )
    ],
)
Session = Annotated[AsyncSession, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/documents", response_model=list[DocumentRead])
async def list_documents(project_id: UUID, user: CurrentUser, session: Session, settings: Config):
    return await DocumentService(session, user.id, settings).list(project_id)


@router.post(
    "/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_document(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    settings: Config,
    file: Annotated[UploadFile, File()],
    category: Annotated[DocumentCategory, Form()] = DocumentCategory.OTHER,
    description: Annotated[str | None, Form(max_length=2000)] = None,
):
    return await DocumentService(session, user.id, settings).upload(
        project_id, file, category, description
    )


@router.patch(
    "/documents/{document_id}", response_model=DocumentRead, dependencies=[Depends(require_csrf)]
)
async def update_document(
    project_id: UUID,
    document_id: UUID,
    data: DocumentUpdate,
    user: CurrentUser,
    session: Session,
    settings: Config,
):
    return await DocumentService(session, user.id, settings).update(project_id, document_id, data)


@router.get("/documents/{document_id}/download")
async def download_document(
    project_id: UUID, document_id: UUID, user: CurrentUser, session: Session, settings: Config
):
    service = DocumentService(session, user.id, settings)
    document = await service._document(project_id, document_id)
    path = service.path_for(document)
    AuditService(session, user.id).record(
        project_id=project_id,
        action="document.downloaded",
        entity_type="project_document",
        entity_id=document.id,
    )
    await session.commit()
    return FileResponse(path, media_type=document.mime_type, filename=document.original_filename)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_document(
    project_id: UUID, document_id: UUID, user: CurrentUser, session: Session, settings: Config
):
    await DocumentService(session, user.id, settings).delete(project_id, document_id)


@router.post("/knowledge/query", response_model=KnowledgeQueryRead)
async def query_knowledge(
    project_id: UUID, data: KnowledgeQuery, user: CurrentUser, session: Session, settings: Config
):
    matches = await DocumentService(session, user.id, settings).search(project_id, data.query)
    return KnowledgeQueryRead(matches=matches)


@router.get("/reports/{report_type}", response_model=ReportRead)
async def report(project_id: UUID, report_type: ReportType, user: CurrentUser, session: Session):
    return await ReportingService(session, user.id).report(project_id, report_type)


@router.get("/reports/{report_type}/pdf")
async def report_pdf(
    project_id: UUID, report_type: ReportType, user: CurrentUser, session: Session
):
    service = ReportingService(session, user.id)
    result = await service.report(project_id, report_type)
    project = await ProjectService(session, user.id).get(project_id)
    return Response(
        content=service.pdf(result),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{project.code}-{report_type.value}.pdf"'
        },
    )


@router.get("/exports/{dataset}/{file_format}")
async def export(
    project_id: UUID, dataset: ExportDataset, file_format: str, user: CurrentUser, session: Session
):
    if file_format not in {"csv", "xlsx"}:
        from app.core.errors import AppError

        raise AppError(
            code="export_format_invalid", message="Unsupported export format.", status_code=422
        )
    project = await ProjectService(session, user.id).get(project_id)
    content = await ExportService(session, user.id).export(project_id, dataset, file_format)
    media = (
        "text/csv; charset=utf-8"
        if file_format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=content,
        media_type=media,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{project.code}-{dataset.value}.{file_format}"'
            )
        },
    )


@router.post(
    "/imports/{target}/preview",
    response_model=ImportPreviewRead,
    dependencies=[Depends(require_csrf)],
)
async def import_preview(
    project_id: UUID,
    target: ImportTarget,
    user: CurrentUser,
    session: Session,
    file: Annotated[UploadFile, File()],
):
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        from app.core.errors import AppError

        raise AppError(
            code="import_file_too_large", message="Import file exceeds 5 MB.", status_code=413
        )
    return await ImportService(session, user.id).preview(
        project_id, target, file.filename or "import", data
    )


@router.post(
    "/imports/{batch_id}/confirm",
    response_model=ImportConfirmRead,
    dependencies=[Depends(require_csrf)],
)
async def import_confirm(project_id: UUID, batch_id: UUID, user: CurrentUser, session: Session):
    return await ImportService(session, user.id).confirm(project_id, batch_id)
