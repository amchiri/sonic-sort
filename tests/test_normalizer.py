"""Tests unitaires pour la normalisation des tags."""
import pytest
from src.normalizer.tag_normalizer import normalize_feat, title_case, normalize_year


def test_normalize_feat_parentheses():
    assert normalize_feat("Song (feat. Artist B)") == "Song (feat. Artist B)"


def test_normalize_feat_ft():
    result = normalize_feat("Song ft. Artist B")
    assert "feat." in result
    assert "Artist B" in result


def test_normalize_feat_featuring():
    result = normalize_feat("Song featuring Artist B")
    assert "feat." in result


def test_normalize_feat_no_feat():
    assert normalize_feat("Simple Song") == "Simple Song"


def test_title_case_basic():
    assert title_case("hello world") == "Hello World"


def test_title_case_articles():
    result = title_case("the sound of music")
    assert result.startswith("The")
    assert " of " in result


def test_title_case_empty():
    assert title_case("") == ""


def test_normalize_year_full_date():
    assert normalize_year("2023-05-15") == "2023"


def test_normalize_year_already_year():
    assert normalize_year("1999") == "1999"


def test_normalize_year_empty():
    assert normalize_year("") == ""


def test_normalize_year_no_digits():
    assert normalize_year("unknown") == ""
