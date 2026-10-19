
import pytest

from src.similarity import cosine_similarity


def test_identical_vectors():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)


def test_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_opposite_vectors():
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


def test_mismatched_dimensions():
    with pytest.raises(ValueError, match="same dimensions"):
        cosine_similarity([1, 2], [1])


def test_zero_vector():
    with pytest.raises(ValueError, match="zero vectors"):
        cosine_similarity([0, 0], [1, 2])


def test_empty_vector():
    with pytest.raises(ValueError, match="cannot be empty"):
        cosine_similarity([], [])
