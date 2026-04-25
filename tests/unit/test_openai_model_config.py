from config.config import Config
from src.llm.openai_provider import OpenAIProvider


def test_default_openai_model_targets_gpt_55():
    assert Config.OPENAI_MODEL == "gpt-5.5"


def test_openai_provider_default_model_targets_gpt_55():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    OpenAIProvider.__init__(provider, api_key="sk-test")

    assert provider.model == "gpt-5.5"
