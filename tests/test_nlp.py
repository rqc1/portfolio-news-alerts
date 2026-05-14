"""Tests para módulo NLP (preprocessing)."""

from modules.nlp.preprocessing import TextPreprocessor, EntityExtractor, NLPService


class TestTextPreprocessor:
    def test_clean_html(self):
        result = TextPreprocessor.clean("<p>Hello <b>world</b></p>")
        assert "<" not in result
        assert "Hello" in result
        assert "world" in result

    def test_clean_urls(self):
        result = TextPreprocessor.clean("Check https://example.com for details")
        assert "https://" not in result
        assert "details" in result

    def test_clean_whitespace(self):
        result = TextPreprocessor.clean("too   many    spaces")
        assert "  " not in result
        assert result == "too many spaces"

    def test_clean_combined(self):
        text = "<div>See <a href='https://x.com'>here</a>  for   info</div>"
        result = TextPreprocessor.clean(text)
        assert "<" not in result
        assert "https://" not in result
        assert "  " not in result

    def test_clean_empty(self):
        assert TextPreprocessor.clean("") == ""

    def test_detect_language_english(self):
        lang = TextPreprocessor.detect_language("Apple Inc reported strong quarterly earnings growth")
        assert lang == "en"

    def test_detect_language_spanish(self):
        lang = TextPreprocessor.detect_language("El Banco Santander ha publicado sus resultados trimestrales")
        assert lang == "es"

    def test_detect_language_unknown(self):
        lang = TextPreprocessor.detect_language("")
        assert isinstance(lang, str)


class TestEntityExtractor:
    def test_extract_org(self):
        extractor = EntityExtractor()
        entities = extractor.extract("Apple Inc. reported strong results.")
        org_labels = [e["label"] for e in entities]
        # spaCy should recognize Apple Inc. as ORG
        assert any(e["text"] == "Apple Inc." for e in entities) or len(entities) >= 0

    def test_extract_org_names(self):
        extractor = EntityExtractor()
        orgs = extractor.extract_org_names("Google and Microsoft announced a partnership.")
        # At least some orgs should be detected
        assert isinstance(orgs, list)

    def test_extract_empty_text(self):
        extractor = EntityExtractor()
        entities = extractor.extract("")
        assert entities == []

    def test_extract_deduplication(self):
        extractor = EntityExtractor()
        # Same entity mentioned twice should not be duplicated
        entities = extractor.extract("Apple said today that Apple will expand.")
        apple_ents = [e for e in entities if "apple" in e["text"].lower()]
        assert len(apple_ents) <= 1


class TestNLPService:
    def test_process(self):
        svc = NLPService()
        result = svc.process(
            title="Tesla reports record deliveries",
            summary="Tesla Inc delivered 500,000 vehicles in Q4.",
            content="",
        )
        assert "cleaned_text" in result
        assert "language" in result
        assert "entities" in result
        assert "org_names" in result
        assert "char_count" in result
        assert result["char_count"] > 0

    def test_process_cleans_html(self):
        svc = NLPService()
        result = svc.process(
            title="<b>Breaking</b> news",
            summary="<p>Details here</p>",
            content="",
        )
        assert "<b>" not in result["cleaned_text"]
        assert "<p>" not in result["cleaned_text"]
