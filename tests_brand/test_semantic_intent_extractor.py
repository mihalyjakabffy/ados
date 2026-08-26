"""
ADOS-M3.1 — brand/llm/extractor.py.

The orchestration contract: LLM first when configured, a deterministic
fallback on anything else, always validated, always traced, and never a
CommandIntent or a Composer call (ADOS-M3.1 §11).
"""

from __future__ import annotations

from brand.llm.extractor import SemanticIntentExtractor, _resolve_default_provider
from brand.llm.observability import clear_traces, get_trace
from brand.llm.provider import LLMProvider, ProviderError, ProviderMetadata
from brand.llm.providers.rule_based_provider import RuleBasedProvider
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent


class _AlwaysFailsProvider(LLMProvider):
    def extract(self, system_prompt, context):
        raise ProviderError("simulated provider failure")


class _StubProvider(LLMProvider):
    def __init__(self, intent: SemanticIntent):
        self._intent = intent

    def extract(self, system_prompt, context):
        return self._intent, ProviderMetadata(provider="stub", model="stub-v1")


def setup_function(_fn):
    clear_traces()


def test_extract_uses_the_injected_provider_when_it_succeeds():
    intent = SemanticIntent(explicit=SemanticFieldValues(action="create", target="document"))
    extractor = SemanticIntentExtractor(provider=_StubProvider(intent))
    result = extractor.extract("anything")
    assert result.metadata.provider == "stub"
    assert result.intent == intent


def test_extract_falls_back_when_the_provider_raises():
    from brand.llm.vocabulary import SemanticField

    extractor = SemanticIntentExtractor(provider=_AlwaysFailsProvider())
    result = extractor.extract("Create a portfolio about the Riverside project.")
    assert result.metadata.provider == "rule-based"
    assert result.intent.resolved(SemanticField.ACTION) == "create"


def test_extract_never_reaches_command_intent_or_composer():
    """No import of brand.creative.intent or brand.creative.composer
    anywhere in the extractor module — ADOS-M3.1 §11's own boundary,
    checked structurally (via the AST's own import nodes, not a
    docstring-fooled substring scan) rather than by behaviour alone."""
    import ast

    import brand.llm.extractor as extractor_module

    with open(extractor_module.__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {"brand.creative.intent", "brand.creative.composer", "brand.creative"}
    assert not (imported_modules & forbidden), imported_modules


def test_extract_records_a_trace_every_time():
    extractor = SemanticIntentExtractor(provider=RuleBasedProvider())
    result = extractor.extract("Review the current draft.")
    assert get_trace(result.trace.request_id) is not None
    assert result.trace.provider == "rule-based"


def test_trace_records_project_and_document_ids_when_given():
    from brand.design_state.build import build_design_state
    from brand.project.model import Document, Project

    document = Document(id="doc-123", project_id="proj-123", name="D")
    project = Project(id="proj-123", name="P", documents=(document,))
    design_state = build_design_state(project, document, None)

    extractor = SemanticIntentExtractor(provider=RuleBasedProvider())
    result = extractor.extract(
        "Review the current draft.", project=project, design_state=design_state,
    )
    assert result.trace.project_id == "proj-123"
    assert result.trace.document_id == "doc-123"


def test_result_validation_matches_the_intent():
    intent = SemanticIntent()  # nothing resolved at all -> BLOCK-level findings
    extractor = SemanticIntentExtractor(provider=_StubProvider(intent))
    result = extractor.extract("anything")
    assert not result.validation.ok


def test_resolve_default_provider_uses_rule_based_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("SEMANTIC_INTENT_LLM_ENABLED", "true")
    provider = _resolve_default_provider()
    assert isinstance(provider, RuleBasedProvider)


def test_resolve_default_provider_uses_rule_based_when_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-for-this-test")
    monkeypatch.setenv("SEMANTIC_INTENT_LLM_ENABLED", "false")
    provider = _resolve_default_provider()
    assert isinstance(provider, RuleBasedProvider)


def test_resolve_default_provider_uses_claude_when_key_present_and_enabled(monkeypatch):
    from brand.llm.providers.claude_provider import ClaudeProvider

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-for-this-test")
    monkeypatch.setenv("SEMANTIC_INTENT_LLM_ENABLED", "true")
    provider = _resolve_default_provider()
    assert isinstance(provider, ClaudeProvider)


def test_extract_result_to_dict_matches_the_api_contract():
    intent = SemanticIntent(explicit=SemanticFieldValues(action="create", target="document"))
    extractor = SemanticIntentExtractor(provider=_StubProvider(intent))
    result = extractor.extract("anything")
    payload = result.to_dict()
    assert set(payload) == {"intent", "validation", "request_id"}
    assert payload["intent"]["explicit"]["action"] == "create"
