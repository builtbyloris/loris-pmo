from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingProvider, EmbeddingPurpose
from app.ai.errors import AIError
from app.core.config import Settings
from app.models.documents import (
    DocumentCategory,
    DocumentChunk,
    DocumentChunkEmbedding,
    DocumentSemanticStatus,
    DocumentStatus,
    ProjectDocument,
)
from app.models.project import Project
from app.schemas.documents import (
    KnowledgeIndexRead,
    KnowledgeMatch,
    KnowledgeQuery,
    KnowledgeQueryRead,
    KnowledgeStatusRead,
    QueryIntent,
    RetrievalDiagnostics,
    RetrievalMode,
)
from app.services.audit import AuditService
from app.services.authorization import AuthorizationService, Capability, accessible_project_ids
from app.services.documents import DocumentService, _tokens

RRF_K = 60


def query_intent(query: str, document_count: int) -> QueryIntent:
    words = set(re.findall(r"[\w-]+", query.lower()))
    if words & {"compare", "comparison", "versus", "vs", "confronta", "confronto"}:
        return QueryIntent.COMPARISON
    if words & {"summarize", "summary", "overview", "riassumi", "sintesi"}:
        return QueryIntent.SUMMARY
    if document_count > 1 or words & {"documents", "sources", "documenti", "fonti"}:
        return QueryIntent.MULTI_DOCUMENT
    return QueryIntent.LOOKUP


def reciprocal_rank_fusion(lexical_order: list[int], semantic_order: list[int]) -> dict[int, float]:
    scores: dict[int, float] = {}
    for rank, index in enumerate(lexical_order, 1):
        scores[index] = scores.get(index, 0) + 1 / (RRF_K + rank)
    for rank, index in enumerate(semantic_order, 1):
        scores[index] = scores.get(index, 0) + 1 / (RRF_K + rank)
    return scores


def cosine_similarity(left: tuple[float, ...], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    right_norm = math.sqrt(sum(value * value for value in right))
    if right_norm <= 0:
        return -1.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / right_norm


class KnowledgeService:
    """Permission-filtered embedding lifecycle and deterministic hybrid retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.session = session
        self.user_id = user_id
        self.settings = settings
        self.provider = embedding_provider
        self.documents = DocumentService(session, user_id, settings)
        self.audit = AuditService(session, user_id)

    async def status(self, project_id: UUID) -> KnowledgeStatusRead:
        documents = await self.documents.list(project_id)
        document_ids = [item.id for item in documents]
        total_chunks = indexed_chunks = 0
        if document_ids:
            total_chunks = int(
                (
                    await self.session.execute(
                        select(func.count(DocumentChunk.id)).where(
                            DocumentChunk.document_id.in_(document_ids)
                        )
                    )
                ).scalar_one()
            )
            indexed_chunks = int(
                (
                    await self.session.execute(
                        select(func.count(DocumentChunkEmbedding.id)).where(
                            DocumentChunkEmbedding.document_id.in_(document_ids),
                            DocumentChunkEmbedding.model == self.provider.model_name,
                            DocumentChunkEmbedding.version == self.settings.embedding_version,
                            DocumentChunkEmbedding.dimensions
                            == self.settings.embedding_dimensions,
                        )
                    )
                ).scalar_one()
            )
        counts = {value: 0 for value in DocumentSemanticStatus}
        for document in documents:
            counts[document.semantic_status] += 1
        return KnowledgeStatusRead(
            provider_available=self.provider.available,
            embedding_model=self.provider.model_name,
            embedding_version=self.settings.embedding_version,
            total_documents=len(documents),
            ready_documents=sum(item.status == DocumentStatus.READY for item in documents),
            indexed_documents=sum(
                item.semantic_status == DocumentSemanticStatus.READY
                and item.embedding_model == self.provider.model_name
                and item.embedding_version == self.settings.embedding_version
                for item in documents
            ),
            partial_documents=counts[DocumentSemanticStatus.PARTIAL],
            failed_documents=counts[DocumentSemanticStatus.FAILED],
            lexical_only_documents=counts[DocumentSemanticStatus.LEXICAL_ONLY],
            total_chunks=total_chunks,
            indexed_chunks=indexed_chunks,
        )

    async def index_document(
        self, project_id: UUID, document_id: UUID, *, require_mutable: bool = True
    ) -> KnowledgeIndexRead:
        if require_mutable:
            await self.documents._project(project_id, mutable=True)
        document = await self.documents._document(project_id, document_id)
        if document.status != DocumentStatus.READY:
            document.semantic_status = DocumentSemanticStatus.NOT_INDEXED
            document.semantic_error = "document_not_ready"
            await self.session.commit()
            return self._index_result(document, 0, 0, 0)
        chunks = list(
            (
                await self.session.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document.id)
                    .order_by(DocumentChunk.chunk_index, DocumentChunk.id)
                )
            ).scalars()
        )
        if not chunks:
            document.semantic_status = DocumentSemanticStatus.LEXICAL_ONLY
            document.semantic_error = "no_extractable_chunks"
            document.embedding_model = None
            document.embedding_version = None
            document.semantic_indexed_at = None
            await self.session.commit()
            return self._index_result(document, 0, 0, 0)
        if not self.provider.available:
            document.semantic_status = DocumentSemanticStatus.LEXICAL_ONLY
            document.semantic_error = "embedding_not_configured"
            document.embedding_model = None
            document.embedding_version = None
            document.semantic_indexed_at = None
            await self.session.commit()
            return self._index_result(document, 0, len(chunks), 0)

        existing = list(
            (
                await self.session.execute(
                    select(DocumentChunkEmbedding).where(
                        DocumentChunkEmbedding.document_id == document.id
                    )
                )
            ).scalars()
        )
        by_chunk = {item.chunk_id: item for item in existing}
        pending: list[DocumentChunk] = []
        reused = 0
        for chunk in chunks:
            stored = by_chunk.get(chunk.id)
            digest = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            if (
                stored is not None
                and stored.content_hash == digest
                and stored.model == self.provider.model_name
                and stored.version == self.settings.embedding_version
                and stored.dimensions == self.settings.embedding_dimensions
            ):
                reused += 1
            else:
                pending.append(chunk)

        document.semantic_status = DocumentSemanticStatus.INDEXING
        document.semantic_error = None
        await self.session.flush()
        generated: list[tuple[DocumentChunk, tuple[float, ...]]] = []
        try:
            size = self.settings.embedding_batch_size
            for offset in range(0, len(pending), size):
                batch = pending[offset : offset + size]
                response = await self.provider.embed(
                    tuple(item.text for item in batch), purpose=EmbeddingPurpose.DOCUMENT
                )
                generated.extend(zip(batch, response.vectors, strict=True))
        except AIError as exc:
            document.semantic_status = (
                DocumentSemanticStatus.PARTIAL if reused else DocumentSemanticStatus.FAILED
            )
            document.semantic_error = exc.code
            document.embedding_model = self.provider.model_name if reused else None
            document.embedding_version = self.settings.embedding_version if reused else None
            await self.session.commit()
            return self._index_result(document, reused, len(chunks), reused)

        for chunk, vector in generated:
            stored = by_chunk.get(chunk.id)
            if stored is None:
                stored = DocumentChunkEmbedding(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    project_id=project_id,
                    provider=self.provider.provider_name,
                    model=self.provider.model_name,
                    version=self.settings.embedding_version,
                    dimensions=len(vector),
                    content_hash="",
                    vector=[],
                    indexed_at=datetime.now(UTC),
                )
                self.session.add(stored)
            stored.provider = self.provider.provider_name
            stored.model = self.provider.model_name
            stored.version = self.settings.embedding_version
            stored.dimensions = len(vector)
            stored.content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            stored.vector = list(vector)
            stored.indexed_at = datetime.now(UTC)
        current_chunk_ids = {item.id for item in chunks}
        for stored in existing:
            if stored.chunk_id not in current_chunk_ids:
                await self.session.delete(stored)
        indexed = reused + len(generated)
        document.semantic_status = (
            DocumentSemanticStatus.READY
            if indexed == len(chunks)
            else DocumentSemanticStatus.PARTIAL
        )
        document.semantic_error = None if indexed == len(chunks) else "partial_index"
        document.embedding_model = self.provider.model_name
        document.embedding_version = self.settings.embedding_version
        document.semantic_indexed_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="knowledge.reindexed",
            entity_type="project_document",
            entity_id=document.id,
            changes={
                "model": self.provider.model_name,
                "version": self.settings.embedding_version,
                "indexed_chunks": indexed,
                "reused_chunks": reused,
                "status": document.semantic_status.value,
            },
        )
        await self.session.commit()
        return self._index_result(document, indexed, len(chunks), reused)

    async def search(self, project_id: UUID, data: KnowledgeQuery) -> KnowledgeQueryRead:
        await self.documents._project(project_id)
        statement = (
            select(DocumentChunk, ProjectDocument, DocumentChunkEmbedding)
            .join(ProjectDocument, ProjectDocument.id == DocumentChunk.document_id)
            .join(Project)
            .outerjoin(
                DocumentChunkEmbedding,
                and_(
                    DocumentChunkEmbedding.chunk_id == DocumentChunk.id,
                    DocumentChunkEmbedding.model == self.provider.model_name,
                    DocumentChunkEmbedding.version == self.settings.embedding_version,
                    DocumentChunkEmbedding.dimensions == self.settings.embedding_dimensions,
                ),
            )
            .where(
                DocumentChunk.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.user_id)),
                ProjectDocument.status == DocumentStatus.READY,
            )
        )
        if data.document_ids:
            statement = statement.where(ProjectDocument.id.in_(data.document_ids))
        if data.categories:
            statement = statement.where(ProjectDocument.category.in_(data.categories))
        if not await AuthorizationService(self.session, self.user_id).can(
            project_id, Capability.FINANCE_READ
        ):
            statement = statement.where(ProjectDocument.category != DocumentCategory.FINANCE)
        rows = list(
            (
                await self.session.execute(
                    statement.order_by(
                        ProjectDocument.created_at.desc(),
                        DocumentChunk.document_id,
                        DocumentChunk.chunk_index,
                    ).limit(self.settings.knowledge_candidate_limit)
                )
            ).all()
        )
        terms = _tokens(data.query)
        lowered = data.query.lower().strip()
        lexical: list[tuple[int, float]] = []
        for index, (chunk, _document, _embedding) in enumerate(rows):
            overlap = terms & _tokens(chunk.text)
            if overlap:
                score = len(overlap) / max(1, len(terms))
                if lowered in chunk.text.lower():
                    score += 0.25
                lexical.append((index, score))
        lexical.sort(key=lambda item: (-item[1], str(rows[item[0]][0].id)))

        semantic: list[tuple[int, float]] = []
        fallback_reason = None
        semantic_available = self.provider.available and any(row[2] is not None for row in rows)
        if semantic_available:
            try:
                response = await self.provider.embed((data.query,), purpose=EmbeddingPurpose.QUERY)
                query_vector = response.vectors[0]
                for index, (_chunk, _document, embedding) in enumerate(rows):
                    if embedding is None:
                        continue
                    score = cosine_similarity(query_vector, embedding.vector)
                    if score > 0:
                        semantic.append((index, score))
                semantic.sort(key=lambda item: (-item[1], str(rows[item[0]][0].id)))
            except AIError as exc:
                semantic_available = False
                fallback_reason = exc.code
        elif not self.provider.available:
            fallback_reason = "embedding_not_configured"
        elif rows:
            fallback_reason = "semantic_index_unavailable"

        mode = RetrievalMode.LEXICAL
        if semantic and lexical:
            mode = RetrievalMode.HYBRID
        elif semantic:
            mode = RetrievalMode.SEMANTIC
        combined: dict[int, float] = {}
        if mode == RetrievalMode.HYBRID:
            combined = reciprocal_rank_fusion(
                [index for index, _score in lexical],
                [index for index, _score in semantic],
            )
        elif mode == RetrievalMode.SEMANTIC:
            combined = dict(semantic)
        else:
            combined = dict(lexical)
        lexical_scores = dict(lexical)
        semantic_scores = dict(semantic)
        ordered = sorted(
            combined,
            key=lambda index: (
                -combined[index],
                rows[index][1].original_filename.lower(),
                rows[index][0].chunk_index,
                str(rows[index][0].id),
            ),
        )
        selected = self._diverse(ordered, rows, data.limit)
        matches = []
        for rank, index in enumerate(selected, 1):
            chunk, document, _embedding = rows[index]
            matches.append(
                KnowledgeMatch(
                    evidence_id=f"document_chunk:{chunk.id}",
                    document_id=document.id,
                    filename=document.original_filename,
                    excerpt=chunk.text[:900],
                    location=chunk.location,
                    score=round(combined[index], 6),
                    lexical_score=(
                        round(lexical_scores[index], 6) if index in lexical_scores else None
                    ),
                    semantic_score=(
                        round(semantic_scores[index], 6) if index in semantic_scores else None
                    ),
                    rank=rank,
                    retrieval_mode=mode,
                    chunk_index=chunk.chunk_index,
                    category=document.category,
                )
            )
        return KnowledgeQueryRead(
            matches=matches,
            diagnostics=RetrievalDiagnostics(
                mode=mode,
                intent=query_intent(data.query, len({item.document_id for item in matches})),
                lexical_candidates=len(lexical),
                semantic_candidates=len(semantic),
                authorized_chunks_considered=len(rows),
                merged_candidates=len(combined),
                selected_chunks=len(matches),
                semantic_available=semantic_available,
                fallback_reason=fallback_reason,
            ),
        )

    @staticmethod
    def _diverse(ordered, rows, limit: int) -> list[int]:
        selected: list[int] = []
        deferred: list[int] = []
        positions: dict[UUID, list[int]] = {}
        for index in ordered:
            chunk, document, _embedding = rows[index]
            nearby = any(
                abs(chunk.chunk_index - value) <= 1 for value in positions.get(document.id, [])
            )
            if nearby:
                deferred.append(index)
                continue
            selected.append(index)
            positions.setdefault(document.id, []).append(chunk.chunk_index)
            if len(selected) == limit:
                return selected
        selected.extend(deferred[: max(0, limit - len(selected))])
        return selected

    @staticmethod
    def _index_result(
        document: ProjectDocument, indexed: int, total: int, reused: int
    ) -> KnowledgeIndexRead:
        return KnowledgeIndexRead(
            document_id=document.id,
            status=document.semantic_status,
            indexed_chunks=indexed,
            total_chunks=total,
            reused_chunks=reused,
            model=document.embedding_model,
            indexed_at=document.semantic_indexed_at,
            error=document.semantic_error,
        )
