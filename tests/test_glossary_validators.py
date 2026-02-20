"""
Glossary validator testleri.
TermRequest ve DefinitionRequest Pydantic modellerini test eder.
"""

import pytest
from src.core.validators import TermRequest, DefinitionRequest


class TestTermRequest:
    def test_valid_term(self):
        req = TermRequest.parse_from_text("Gradient Descent")
        assert req.term == "Gradient Descent"

    def test_empty_term_raises(self):
        with pytest.raises(ValueError):
            TermRequest.parse_from_text("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            TermRequest.parse_from_text("   ")

    def test_too_long_term_raises(self):
        with pytest.raises(ValueError):
            TermRequest.parse_from_text("a" * 201)

    def test_whitespace_stripped(self):
        req = TermRequest.parse_from_text("  Docker  ")
        assert req.term == "Docker"


class TestDefinitionRequest:
    def test_valid_definition(self):
        req = DefinitionRequest.parse_from_text("Gradient Descent | Bir optimizasyon algoritmasi")
        assert req.term == "Gradient Descent"
        assert req.definition == "Bir optimizasyon algoritmasi"

    def test_missing_separator_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text("Gradient Descent aciklama yok")

    def test_empty_definition_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text("Gradient Descent | ")

    def test_empty_term_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text(" | bir aciklama")

    def test_definition_with_multiple_pipes(self):
        req = DefinitionRequest.parse_from_text("API | Application | Programming Interface")
        assert req.term == "API"
        assert req.definition == "Application | Programming Interface"

    def test_too_long_definition_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text("Docker | " + "a" * 2001)
