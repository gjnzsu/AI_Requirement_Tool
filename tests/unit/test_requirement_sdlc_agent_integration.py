from unittest.mock import Mock

from langchain_core.messages import AIMessage

from src.agent.agent_graph import ChatbotAgent
from src.services.requirement_workflow_service import RequirementWorkflowResult
from src.services.requirement_sdlc_agent_service import (
    RequirementSdlcAgentTurnResult,
)
from src.services.project_status_agent_service import ProjectStatusAgentTurnResult


def test_requirement_sdlc_agent_runtime_state_round_trips():
    agent = ChatbotAgent.__new__(ChatbotAgent)

    agent.load_requirement_sdlc_agent_state(
        {"stage": "confirmation", "awaiting_confirmation": True}
    )

    exported = agent.export_requirement_sdlc_agent_state()

    assert exported == {"stage": "confirmation", "awaiting_confirmation": True}
    exported["stage"] = "mutated"
    assert agent.export_requirement_sdlc_agent_state()["stage"] == "confirmation"


def test_switching_agent_mode_to_auto_clears_pending_requirement_state():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent.load_requirement_sdlc_agent_state(
        {"stage": "confirmation", "awaiting_confirmation": True}
    )

    agent.set_selected_agent_mode("auto")

    assert agent.get_selected_agent_mode() == "auto"
    assert agent.export_requirement_sdlc_agent_state() is None


def test_handle_requirement_sdlc_agent_delegates_to_service_and_persists_state():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent._refresh_application_services = Mock()
    agent.requirement_sdlc_agent_service = Mock()
    agent.requirement_sdlc_agent_service.handle_turn.return_value = (
        RequirementSdlcAgentTurnResult(
            response_text="Preview ready",
            response_kind="preview",
            pending_state={"stage": "confirmation", "awaiting_confirmation": True},
        )
    )
    agent.load_requirement_sdlc_agent_state({"stage": "analysis"})

    state = {
        "messages": [],
        "user_input": "turn this into a requirement",
        "conversation_history": [{"role": "user", "content": "Need login auditing"}],
    }

    result = agent._handle_requirement_sdlc_agent(state)

    agent._refresh_application_services.assert_called_once_with()
    agent.requirement_sdlc_agent_service.handle_turn.assert_called_once_with(
        user_input="turn this into a requirement",
        conversation_history=[{"role": "user", "content": "Need login auditing"}],
        pending_state={"stage": "analysis"},
    )
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == "Preview ready"
    assert agent.export_requirement_sdlc_agent_state()["awaiting_confirmation"] is True


def test_handle_requirement_sdlc_agent_exports_latest_workflow_progress_when_completed():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent._refresh_application_services = Mock()
    agent.requirement_sdlc_agent_service = Mock()
    agent.requirement_sdlc_agent_service.handle_turn.return_value = (
        RequirementSdlcAgentTurnResult(
            response_text="Completed",
            response_kind="completed",
            pending_state=None,
            workflow_result=RequirementWorkflowResult(
                success=True,
                response_text="Completed",
                workflow_progress=[
                    {"step": "jira", "label": "Create Jira", "status": "completed"},
                ],
            ),
        )
    )
    agent.load_requirement_sdlc_agent_state({"stage": "confirmation"})
    agent.load_latest_requirement_workflow_progress(None)

    result = agent._handle_requirement_sdlc_agent(
        {
            "messages": [],
            "user_input": "approve",
            "conversation_history": [{"role": "user", "content": "Need login auditing"}],
        }
    )

    assert result["messages"][-1].content == "Completed"
    assert agent.export_latest_requirement_workflow_progress() == [
        {"step": "jira", "label": "Create Jira", "status": "completed"},
    ]


def test_switching_agent_mode_to_auto_clears_pending_pm_status_state():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent.load_pm_status_agent_state({"stage": "confirmation", "awaiting_confirmation": True})

    agent.set_selected_agent_mode("auto")

    assert agent.get_selected_agent_mode() == "auto"
    assert agent.export_pm_status_agent_state() is None


def test_handle_pm_status_agent_delegates_to_service_and_persists_state():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent._refresh_application_services = Mock()
    agent.project_status_agent_service = Mock()
    agent.project_status_agent_service.handle_turn.return_value = ProjectStatusAgentTurnResult(
        response_text="PM Status\nHealth: Green",
        response_kind="report",
        pending_state={"stage": "preview"},
    )
    agent.load_pm_status_agent_state({"stage": "analysis"})

    state = {
        "messages": [],
        "user_input": "generate PM status for AIP",
        "conversation_history": [{"role": "user", "content": "status pls"}],
    }

    result = agent._handle_pm_status_agent(state)

    agent._refresh_application_services.assert_called_once_with()
    agent.project_status_agent_service.handle_turn.assert_called_once_with(
        user_input="generate PM status for AIP",
        conversation_history=[{"role": "user", "content": "status pls"}],
        pending_state={"stage": "analysis"},
    )
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == "PM Status\nHealth: Green"
    assert agent.export_pm_status_agent_state() == {"stage": "preview"}


def test_handle_pm_status_agent_exports_latest_workflow_progress():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent._refresh_application_services = Mock()
    agent.project_status_agent_service = Mock()
    agent.project_status_agent_service.handle_turn.return_value = ProjectStatusAgentTurnResult(
        response_text="Published",
        response_kind="completed",
        pending_state=None,
        workflow_progress=[
            {"step": "pm_writeback", "label": "Publish PM status", "status": "completed"}
        ],
    )
    agent.load_latest_pm_status_workflow_progress(None)

    result = agent._handle_pm_status_agent(
        {
            "messages": [],
            "user_input": "approve",
            "conversation_history": [],
        }
    )

    assert result["messages"][-1].content == "Published"
    assert agent.export_latest_pm_status_workflow_progress() == [
        {"step": "pm_writeback", "label": "Publish PM status", "status": "completed"}
    ]
