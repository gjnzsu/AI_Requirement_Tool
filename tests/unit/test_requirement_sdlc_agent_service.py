from types import SimpleNamespace
from unittest.mock import Mock

from src.services.requirement_sdlc_agent_service import (
    RequirementSdlcAgentService,
)
from src.services.requirement_workflow_service import RequirementWorkflowResult


class FakeSkillLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self.response)


class DualMethodSkillLLM:
    def __init__(self, *, invoke_response: str, generate_response_value: str):
        self.invoke_response = invoke_response
        self.generate_response_value = generate_response_value
        self.invoke_calls = []
        self.generate_response_calls = []

    def invoke(self, messages):
        self.invoke_calls.append(messages)
        return SimpleNamespace(content=self.invoke_response)

    def generate_response(self, **kwargs):
        self.generate_response_calls.append(kwargs)
        return self.generate_response_value


def test_handle_turn_creates_preview_and_waits_for_confirmation():
    llm = FakeSkillLLM(
        """
        {
          "status": "ready_for_confirmation",
          "assistant_message": "Preview ready",
          "draft": {
            "summary": "Add login auditing",
            "problem_goal": "Track all login attempts",
            "business_value": "Improves traceability",
            "scope_notes": "Authentication only",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "assumptions": ["Existing auth system remains unchanged"],
            "open_questions": [],
            "priority": "High"
          }
        }
        """
    )
    workflow_service = Mock()
    service = RequirementSdlcAgentService(
        llm_provider=llm,
        workflow_service=workflow_service,
    )

    result = service.handle_turn(
        user_input="Help me turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "preview"
    assert "Add login auditing" in result.response_text
    assert "Reply with 'approve'" in result.response_text
    assert result.pending_state["stage"] == "confirmation"
    assert result.pending_state["awaiting_confirmation"] is True
    assert result.pending_state["draft"]["description"].startswith("Problem / Goal:")
    workflow_service.execute_backlog_data.assert_not_called()


def test_handle_turn_returns_question_when_more_information_is_needed():
    llm = FakeSkillLLM(
        """
        {
          "status": "needs_information",
          "assistant_message": "Which user roles should be included in the first release?",
          "draft": {
            "summary": "Add login auditing",
            "problem_goal": "Track all login attempts",
            "business_value": "Improves traceability",
            "scope_notes": "",
            "acceptance_criteria": [],
            "assumptions": [],
            "open_questions": ["Which user roles should be included in the first release?"],
            "priority": "Medium"
          }
        }
        """
    )
    service = RequirementSdlcAgentService(
        llm_provider=llm,
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert result.response_text == "Which user roles should be included in the first release?"
    assert result.pending_state["stage"] == "analysis"
    assert result.pending_state["awaiting_confirmation"] is False
    assert result.pending_state["draft"]["open_questions"] == [
        "Which user roles should be included in the first release?"
    ]


def test_handle_turn_does_not_block_on_priority_only_follow_up():
    llm = FakeSkillLLM(
        """
        {
          "status": "needs_information",
          "assistant_message": "What priority should we assign to this requirement?",
          "draft": {
            "summary": "Add login auditing",
            "problem_goal": "Track all login attempts",
            "business_value": "Improves traceability",
            "scope_notes": "Authentication only",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "assumptions": [],
            "open_questions": ["What priority should we assign to this requirement?"],
            "priority": "",
            "invest_analysis": "Independent and testable"
          }
        }
        """
    )
    service = RequirementSdlcAgentService(
        llm_provider=llm,
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "preview"
    assert "defaulted the priority to Medium" in result.response_text
    assert "Priority: Medium" in result.response_text
    assert result.pending_state["draft"]["priority"] == "Medium"
    assert result.pending_state["draft"]["open_questions"] == []


def test_handle_turn_unknown_status_falls_back_to_safe_question():
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM(
            """
            {
              "status": "ship_it",
              "assistant_message": "Preview ready",
              "draft": {
                "summary": "Add login auditing",
                "business_value": "Improves traceability"
              }
            }
            """
        ),
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert "couldn't safely interpret" in result.response_text.lower()
    assert result.pending_state["stage"] == "analysis"
    assert result.pending_state["awaiting_confirmation"] is False


def test_handle_turn_malformed_json_returns_controlled_question():
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM("not-json"),
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert "couldn't safely interpret" in result.response_text.lower()
    assert result.pending_state["stage"] == "analysis"
    assert result.pending_state["awaiting_confirmation"] is False


def test_handle_turn_non_dict_draft_payload_returns_controlled_question():
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM(
            """
            {
              "status": "needs_information",
              "assistant_message": "Need more detail",
              "draft": "oops"
            }
            """
        ),
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert "couldn't safely interpret" in result.response_text.lower()
    assert result.pending_state["stage"] == "analysis"
    assert result.pending_state["awaiting_confirmation"] is False


def test_handle_turn_malformed_typed_preview_fields_are_normalized_safely():
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM(
            """
            {
              "status": "ready_for_confirmation",
              "assistant_message": ["Preview ready"],
              "draft": {
                "summary": ["oops"],
                "problem_goal": 42,
                "business_value": {"value": "traceability"},
                "scope_notes": ["auth only"],
                "acceptance_criteria": ["Every login attempt is recorded", 99],
                "assumptions": {"note": "Keep auth unchanged"},
                "open_questions": null,
                "priority": {"level": "High"},
                "invest_analysis": ["testable"]
              }
            }
            """
        ),
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "preview"
    assert "Preview ready" in result.response_text
    assert "Summary: ['oops']" in result.response_text
    assert "Priority: {'level': 'High'}" in result.response_text
    assert result.pending_state["draft"]["summary"] == "['oops']"
    assert result.pending_state["draft"]["priority"] == "{'level': 'High'}"
    assert result.pending_state["draft"]["business_value"] == "{'value': 'traceability'}"


def test_handle_turn_malformed_typed_question_fields_are_normalized_safely():
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM(
            """
            {
              "status": "needs_information",
              "assistant_message": {"text": "Which roles are in scope?"},
              "draft": {
                "summary": ["oops"],
                "priority": {"level": "Medium"}
              }
            }
            """
        ),
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert result.response_text == "{'text': 'Which roles are in scope?'}"
    assert result.pending_state["draft"]["summary"] == "['oops']"
    assert result.pending_state["draft"]["priority"] == "{'level': 'Medium'}"


def test_handle_turn_revision_request_reanalyzes_and_returns_updated_preview():
    llm = FakeSkillLLM(
        """
        {
          "status": "ready_for_confirmation",
          "assistant_message": "Updated preview ready",
          "draft": {
            "summary": "Add admin login auditing",
            "problem_goal": "Track admin login attempts only",
            "business_value": "Improves traceability",
            "scope_notes": "Admin authentication only",
            "acceptance_criteria": ["Every admin login attempt is recorded"],
            "assumptions": [],
            "open_questions": [],
            "priority": "High"
          }
        }
        """
    )
    service = RequirementSdlcAgentService(
        llm_provider=llm,
        workflow_service=Mock(),
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "draft": {
            "summary": "Add login auditing",
            "business_value": "Improves traceability",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "priority": "High",
            "invest_analysis": "Independent, valuable, testable",
            "description": "Business Value: Improves traceability",
        },
    }

    result = service.handle_turn(
        user_input="Please narrow this to admin logins only",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "preview"
    assert "Add admin login auditing" in result.response_text
    assert result.pending_state["stage"] == "confirmation"
    assert result.pending_state["awaiting_confirmation"] is True
    assert result.pending_state["draft"]["summary"] == "Add admin login auditing"
    assert llm.calls


def test_handle_turn_cancel_clears_pending_state_without_execution():
    workflow_service = Mock()
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM("{}"),
        workflow_service=workflow_service,
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "draft": {"summary": "Add login auditing"},
    }

    result = service.handle_turn(
        user_input="cancel",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "cancelled"
    assert result.pending_state is None
    assert "Nothing was created" in result.response_text
    workflow_service.execute_backlog_data.assert_not_called()


def test_handle_turn_approval_executes_structured_workflow():
    workflow_service = Mock()
    workflow_service.execute_backlog_data.return_value = RequirementWorkflowResult(
        success=True,
        response_text="workflow complete",
        backlog_data={"summary": "Add login auditing"},
        jira_result={
            "success": True,
            "key": "PROJ-123",
            "link": "https://jira.example/browse/PROJ-123",
        },
        confluence_result={
            "success": True,
            "title": "PROJ-123: Add login auditing",
            "link": "https://wiki.example/pages/123",
        },
    )
    service = RequirementSdlcAgentService(
        llm_provider=FakeSkillLLM("{}"),
        workflow_service=workflow_service,
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "draft": {
            "summary": "Add login auditing",
            "business_value": "Improves traceability",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves traceability",
        },
    }

    result = service.handle_turn(
        user_input="approve",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "completed"
    assert result.response_text == "workflow complete"
    assert result.pending_state is None
    assert result.workflow_result.success is True
    workflow_service.execute_backlog_data.assert_called_once_with(
        pending_state["draft"]
    )


def test_generate_llm_response_prefers_invoke_when_provider_supports_both():
    llm = DualMethodSkillLLM(
        invoke_response="""
        {
          "status": "needs_information",
          "assistant_message": "Which roles are in scope?",
          "draft": {"summary": "Add login auditing"}
        }
        """,
        generate_response_value="""
        {
          "status": "ready_for_confirmation",
          "assistant_message": "Wrong path",
          "draft": {"summary": "Wrong draft"}
        }
        """,
    )
    service = RequirementSdlcAgentService(
        llm_provider=llm,
        workflow_service=Mock(),
    )

    result = service.handle_turn(
        user_input="Turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "question"
    assert result.response_text == "Which roles are in scope?"
    assert len(llm.invoke_calls) == 1
    assert llm.generate_response_calls == []
