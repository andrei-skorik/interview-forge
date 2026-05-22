from uuid import UUID

import structlog

from lib.db.client import get_service_client
from lib.schemas.messages import SimilarQuestion

logger = structlog.get_logger(__name__)


def add_embedding(
    user_id: UUID,
    session_id: UUID,
    message_id: UUID,
    question_text: str,
    embedding: list[float],
    domain: str,
) -> None:
    """Insert a question embedding into question_embeddings. Ignores conflicts on message_id."""
    try:
        service_client = get_service_client()
        service_client.table("question_embeddings").insert(
            {
                "user_id": str(user_id),
                "session_id": str(session_id),
                "message_id": str(message_id),
                "question_text": question_text,
                "embedding": embedding,
                "domain": domain,
            }
        ).execute()
    except Exception as exc:
        # On UniqueViolation or any conflict — ignore silently
        err_str = str(exc)
        if "unique" in err_str.lower() or "duplicate" in err_str.lower():
            return
        logger.warning(
            "add_embedding_failed",
            message_id=str(message_id),
            error=err_str,
        )


def find_similar_questions(
    query_embedding: list[float],
    user_id: UUID,
    domain: str,
    *,
    threshold: float = 0.92,
    max_results: int = 5,
) -> list[SimilarQuestion]:
    """Call the find_similar_questions RPC and return SimilarQuestion list."""
    try:
        service_client = get_service_client()
        response = service_client.rpc(
            "find_similar_questions",
            {
                "query_embedding": query_embedding,
                "target_user_id": str(user_id),
                "target_domain": domain,
                "similarity_threshold": threshold,
                "max_results": max_results,
            },
        ).execute()
        rows = response.data or []
        return [
            SimilarQuestion(
                id=row["id"],
                question_text=row["question_text"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]
    except Exception as exc:
        logger.warning(
            "find_similar_questions_failed",
            user_id=str(user_id),
            domain=domain,
            error=str(exc),
        )
        return []
