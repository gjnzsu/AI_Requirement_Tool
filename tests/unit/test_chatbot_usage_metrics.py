from types import SimpleNamespace

from src.chatbot import Chatbot


class FakeAgent:
    def __init__(self):
        self.llm_callback = SimpleNamespace(
            total_prompt_tokens=10,
            total_completion_tokens=5,
        )
        self.selected_agent_mode = None

    def set_selected_agent_mode(self, agent_mode):
        self.selected_agent_mode = agent_mode

    def invoke(self, user_input, conversation_history, precomputed_intent=None):
        return "response"


class FakeConfig:
    LLM_PROVIDER = "deepseek"
    OPENAI_MODEL = "gpt-4o"
    GEMINI_MODEL = "gemini-pro"
    DEEPSEEK_MODEL = "deepseek-v4-flash"

    @classmethod
    def get_llm_model(cls):
        return cls.DEEPSEEK_MODEL


def make_agent_chatbot(provider_name):
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.provider_name = provider_name
    chatbot.config = FakeConfig
    chatbot.use_agent = True
    chatbot.agent = FakeAgent()
    chatbot.use_persistent_memory = False
    chatbot.memory_manager = None
    chatbot.conversation_id = "conv-test"
    chatbot.conversation_history = []
    chatbot.selected_agent_mode = "auto"
    chatbot.last_usage = None
    chatbot._precomputed_intent_for_next_response = None
    return chatbot


def test_agent_usage_labels_openai_model_when_provider_switched_from_deepseek_default():
    chatbot = make_agent_chatbot("openai")

    chatbot.get_response("hello")

    assert chatbot.last_usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "provider": "openai",
        "model": "gpt-4o",
    }
