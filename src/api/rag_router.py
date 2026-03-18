"""
Router para endpoints de RAG.

Endpoints para gestión de Knowledge Base:
- Ingestión de documentos
- Búsqueda
- Notificaciones de Flowify
"""

import hashlib

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

rag_router = APIRouter(prefix="/rag", tags=["RAG"])


class RagSearchRequest(BaseModel):
    """Request para búsqueda RAG."""
    empresa_id: int = Field(...)
    empresa_slug: str | None = Field(None)
    query: str = Field(...)
    top_k: int | None = Field(None)


@rag_router.post("/ingest/upload")
async def rag_ingest_upload(
    file: UploadFile = File(...),
    empresa_id: int = Form(...),
    empresa_slug: str = Form(...),
    doc_id: str | None = Form(None),
    tags: str | None = Form(None),
):
    """
    Ingesta un documento al RAG vía upload directo.
    
    El documento se procesa y almacena en el vector store.
    """
    from src.rag.ingest_worker import enqueue_rag_job
    from src.rag.vector_store import ensure_collection

    try:
        content = await file.read()
        file_hash = hashlib.md5(content).hexdigest()
        
        doc_id = doc_id or f"doc_{file_hash[:8]}"
        
        await ensure_collection(str(empresa_id))
        
        await enqueue_rag_job({
            "empresa_id": empresa_id,
            "empresa_slug": empresa_slug,
            "doc_id": doc_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "content": content.decode("utf-8", errors="replace"),
            "tags": tags.split(",") if tags else [],
        })
        
        return {
            "status": "queued",
            "doc_id": doc_id,
            "empresa_id": empresa_id,
            "filename": file.filename,
        }
        
    except Exception as e:
        logger.error("Error en rag_ingest_upload", error=str(e))
        return {"error": str(e)}, 500


@rag_router.post("/ingest/notify")
async def rag_ingest_notify(request: Request):
    """
    Recibe notificación de Flowify de nuevo documento en KB.
    
    Flowify envía:
    - empresa_id
    - doc_id
    - content
    - metadata
    """
    from src.rag.ingest_worker import enqueue_rag_job
    from src.rag.vector_store import ensure_collection

    try:
        body = await request.json()
        
        empresa_id = body.get("empresa_id")
        doc_id = body.get("doc_id")
        content = body.get("content", "")
        
        if not empresa_id:
            return {"error": "empresa_id required"}, 400
        
        await ensure_collection(str(empresa_id))
        
        await enqueue_rag_job({
            "empresa_id": empresa_id,
            "empresa_slug": body.get("empresa_slug", ""),
            "doc_id": doc_id or f"doc_{hashlib.md5(content.encode()).hexdigest()[:8]}",
            "content": content,
            "title": body.get("title", ""),
            "tags": body.get("tags", []),
        })
        
        return {
            "status": "queued",
            "doc_id": doc_id,
            "empresa_id": empresa_id,
        }
        
    except Exception as e:
        logger.error("Error en rag_ingest_notify", error=str(e))
        return {"error": str(e)}, 500


@rag_router.post("/search")
async def rag_search(req: RagSearchRequest):
    """
    Realiza búsqueda en el Knowledge Base.
    """
    from src.rag.vector_store import reranked_search

    try:
        docs = await reranked_search(
            str(req.empresa_id),
            req.query,
            req.top_k or settings.rag_search_top_k or 5,
        )
        
        return {
            "query": req.query,
            "empresa_id": req.empresa_id,
            "results": docs,
            "count": len(docs),
        }
        
    except Exception as e:
        logger.error("Error en rag_search", error=str(e))
        return {"error": str(e)}


@rag_router.get("/documents/{empresa_id}")
async def list_documents(empresa_id: str):
    """
    Lista los documentos ingestionados para una empresa.
    """
    from src.rag.vector_store import list_docs
    try:
        return list_docs(empresa_id)
    except Exception as e:
        logger.error("Error listando documentos", error=str(e))
        return {"error": str(e)}


@rag_router.delete("/documents/{empresa_id}/{doc_id}")
async def delete_document(empresa_id: str, doc_id: str):
    """
    Elimina un documento de la base de conocimiento.
    """
    from src.rag.vector_store import delete_doc_complete
    try:
        success = delete_doc_complete(empresa_id, doc_id)
        if success:
            return {"status": "deleted", "doc_id": doc_id}
        else:
            return {"error": "Could not delete document"}, 400
    except Exception as e:
        logger.error("Error eliminando documento", error=str(e))
        return {"error": str(e)}
