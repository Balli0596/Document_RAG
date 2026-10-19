
import pytest

from src.rag_chain import generate_answer, FALLBACK_ANSWER


class EmptyCollection:
    def count(self):
        return 0


def test_no_evidence_returns_fallback():
    result = generate_answer(
        question="What is the document about?",
        collection=EmptyCollection(),
    )

    assert result["answer"] == FALLBACK_ANSWER
    assert result["sources"] == []


def test_blank_question_is_rejected():
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_answer(
            question="   ",
            collection=EmptyCollection(),
        )
