import concurrent.futures

from langchain_core.messages import AIMessage, HumanMessage

from src.services.chat_response_service import ChatResponseService
from src.services.coze_agent_service import CozeAgentService
from src.services.general_chat_service import GeneralChatService
from src.services.rag_query_service import RagQueryService


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return AIMessage(content=self.response)


class FakeRagService:
    def __init__(self):
        self.vector_store = self
        self.get_context_calls = []
        self.retrieve_calls = []

    def get_document(self, doc_id):
        if doc_id == "jira_issue:PROJ-123":
            return {"content": "Direct Jira content"}
        if doc_id == "confluence_page:PROJ-123:overview":
            return {"content": "Related Confluence content"}
        return None

    def list_documents(self):
        return [{"id": "confluence_page:PROJ-123:overview"}]

    def get_context(self, user_input, top_k):
        self.get_context_calls.append((user_input, top_k))
        return "Semantic context"

    def retrieve(self, user_input, top_k=3):
        self.retrieve_calls.append((user_input, top_k))
        return [{"content": "Chunk A"}, {"content": "Chunk B"}]


class FakeChatResponseService:
    def __init__(self):
        self.calls = []

    def generate_reply(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs["messages"] + [AIMessage(content="Delegated response")]


class FakeCozeClient:
    def __init__(self, *, configured=True, result=None, side_effect=None):
        self.configured = configured
        self.result = result or {"success": True, "response": "Coze says hi"}
        self.side_effect = side_effect
        self.calls = []

    def is_configured(self):
        return self.configured

    def execute_agent(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect:
            raise self.side_effect
        return self.result


def test_chat_response_service_appends_llm_reply():
    service = ChatResponseService(
        llm_provider=FakeLLM("hello back"),
        provider_name="openai",
    )

    messages = service.generate_reply(
        messages=[],
        user_input="hello",
        system_prompt="You are helpful.",
    )

    assert len(messages) == 3
    assert isinstance(messages[-1], AIMessage)
    assert messages[-1].content == "hello back"


def test_general_chat_service_enriches_confluence_queries_before_llm_call():
    response_service = FakeChatResponseService()
    service = GeneralChatService(
        chat_response_service=response_service,
        retrieve_confluence_page_info=lambda **kwargs: {
            "success": True,
            "title": "Requirement page",
            "link": "https://wiki.example/page",
            "content": "Important requirement details",
        },
    )

    result = service.handle(
        user_input="tell me about confluence page for PROJ-123",
        messages=[],
        confluence_result={"success": True, "id": "123", "title": "Requirement page"},
    )

    assert result["page_info"]["success"] is True
    assert "Confluence Page Information" in response_service.calls[0]["user_input"]
    assert isinstance(result["messages"][-1], AIMessage)


def test_rag_query_service_uses_direct_lookup_before_semantic_search():
    response_service = FakeChatResponseService()
    rag_service = FakeRagService()
    service = RagQueryService(
        rag_service=rag_service,
        chat_response_service=response_service,
    )

    result = service.handle(
        user_input="What is the status of PROJ-123?",
        messages=[],
    )

    assert rag_service.get_context_calls == []
    assert result["rag_context"] == ["Chunk A", "Chunk B"]
    assert "Direct Jira content" in response_service.calls[0]["user_input"]


def test_coze_agent_service_returns_timeout_message_and_payload():
    service = CozeAgentService(
        coze_client=FakeCozeClient(side_effect=concurrent.futures.TimeoutError()),
        timeout_seconds=5.0,
    )

    result = service.handle(
        user_input="give me an AI daily report",
        previous_result=None,
    )

    assert result["coze_result"]["success"] is False
    assert result["coze_result"]["error_type"] == "timeout"
    assert "timed out" in result["message"].lower()
