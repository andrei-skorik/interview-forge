"""pgvector similarity search tests.

Unit tests with mocked supabase RPC.
"""

from uuid import uuid4

import pytest

from lib.db.embeddings import find_similar_questions
from lib.schemas.messages import SimilarQuestion


def test_find_similar_questions_returns_list(mocker) -> None:
    """find_similar_questions should return list[SimilarQuestion]."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = [
        {"id": str(uuid4()), "question_text": "What is asyncio?", "similarity": 0.95},
        {"id": str(uuid4()), "question_text": "How does event loop work?", "similarity": 0.93},
    ]

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_service.return_value.rpc.return_value.execute.return_value = mock_rpc_result

    embedding = [0.1] * 4096
    result = find_similar_questions(embedding, uuid4(), "backend")

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(q, SimilarQuestion) for q in result)


def test_find_similar_questions_empty_result(mocker) -> None:
    """Should return empty list when no similar questions found."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = []

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_service.return_value.rpc.return_value.execute.return_value = mock_rpc_result

    result = find_similar_questions([0.1] * 4096, uuid4(), "frontend")
    assert result == []


def test_similarity_threshold_passed_to_rpc(mocker) -> None:
    """threshold parameter should be forwarded to supabase RPC."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = []

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_rpc = mock_service.return_value.rpc
    mock_rpc.return_value.execute.return_value = mock_rpc_result

    find_similar_questions([0.1] * 4096, uuid4(), "backend", threshold=0.95)

    # Second positional arg to rpc() is the params dict
    call_params = mock_rpc.call_args[0][1]
    assert call_params["similarity_threshold"] == 0.95


def test_max_results_passed_to_rpc(mocker) -> None:
    """max_results parameter should be forwarded to supabase RPC."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = []

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_rpc = mock_service.return_value.rpc
    mock_rpc.return_value.execute.return_value = mock_rpc_result

    find_similar_questions([0.1] * 4096, uuid4(), "backend", max_results=3)

    call_params = mock_rpc.call_args[0][1]
    assert call_params["max_results"] == 3


def test_user_id_passed_as_string_to_rpc(mocker) -> None:
    """user_id UUID should be converted to string when passed to RPC."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = []

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_rpc = mock_service.return_value.rpc
    mock_rpc.return_value.execute.return_value = mock_rpc_result

    user_id = uuid4()
    find_similar_questions([0.1] * 4096, user_id, "backend")

    call_params = mock_rpc.call_args[0][1]
    assert call_params["target_user_id"] == str(user_id)


def test_domain_passed_to_rpc(mocker) -> None:
    """domain string should be forwarded to supabase RPC."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = []

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_rpc = mock_service.return_value.rpc
    mock_rpc.return_value.execute.return_value = mock_rpc_result

    find_similar_questions([0.1] * 4096, uuid4(), "data_ml")

    call_params = mock_rpc.call_args[0][1]
    assert call_params["target_domain"] == "data_ml"


def test_similar_question_fields_populated(mocker) -> None:
    """Returned SimilarQuestion objects must have id, question_text, similarity."""
    question_id = str(uuid4())
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = [
        {
            "id": question_id,
            "question_text": "Explain the GIL in Python.",
            "similarity": 0.97,
        }
    ]

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_service.return_value.rpc.return_value.execute.return_value = mock_rpc_result

    result = find_similar_questions([0.1] * 4096, uuid4(), "backend")

    assert len(result) == 1
    assert str(result[0].id) == question_id
    assert result[0].question_text == "Explain the GIL in Python."
    assert result[0].similarity == pytest.approx(0.97)


def test_exception_in_rpc_returns_empty_list(mocker) -> None:
    """Exception from supabase RPC must be caught and empty list returned."""
    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_service.return_value.rpc.side_effect = Exception("Connection refused")

    result = find_similar_questions([0.1] * 4096, uuid4(), "backend")

    assert result == []


def test_none_data_in_rpc_result_returns_empty_list(mocker) -> None:
    """None .data from RPC must return empty list (not raise AttributeError)."""
    mock_rpc_result = mocker.MagicMock()
    mock_rpc_result.data = None

    mock_service = mocker.patch("lib.db.embeddings.get_service_client")
    mock_service.return_value.rpc.return_value.execute.return_value = mock_rpc_result

    result = find_similar_questions([0.1] * 4096, uuid4(), "backend")
    assert result == []
