from config.config import Config
from src.llm.openai_provider import OpenAIProvider


def test_default_openai_model_targets_gpt_54():
    assert Config.OPENAI_MODEL == "gpt-5.4"


def test_openai_provider_default_model_targets_gpt_54(monkeypatch):
    import src.llm.openai_provider as openai_provider_module

    monkeypatch.setattr(openai_provider_module, "OpenAI", lambda **_: object())

    provider = OpenAIProvider.__new__(OpenAIProvider)
    OpenAIProvider.__init__(provider, api_key="sk-test")

    assert provider.model == "gpt-5.4"
