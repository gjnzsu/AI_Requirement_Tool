from langchain_core.messages import AIMessage, HumanMessage

from src.agent.requirement_workflow import (
    build_backlog_generation_prompt,
    build_requirement_context,
    format_confluence_content,
)


def test_build_requirement_context_includes_recent_messages_and_history():
    context = build_requirement_context(
        messages=[
            HumanMessage(content="Create a Jira issue"),
            AIMessage(content="Sure, tell me more"),
        ],
        conversation_history=[
            {"role": "user", "content": "Need an audit trail"},
            {"role": "assistant", "content": "Let's capture acceptance criteria"},
        ],
    )

    assert "User: Create a Jira issue" in context
    assert "Assistant: Sure, tell me more" in context
    assert "Conversation History" in context
    assert "user: Need an audit trail" in context


def test_build_backlog_generation_prompt_includes_context_and_request():
    prompt = build_backlog_generation_prompt(
        context_text="User: Create a Jira issue",
        user_input="Please create an auth backlog",
    )

    assert "User: Create a Jira issue" in prompt
    assert "User request: Please create an auth backlog" in prompt
    assert '"summary"' in prompt
    assert '"description"' in prompt


def test_format_confluence_content_renders_backlog_and_evaluation_sections():
    html_content = format_confluence_content(
        issue_key="PROJ-123",
        backlog_data={
            "summary": "Add login audit trail",
            "priority": "High",
            "business_value": "Improves traceability",
            "acceptance_criteria": ["Every login event is recorded"],
            "invest_analysis": "Small and testable",
        },
        evaluation={
            "overall_maturity_score": 90,
            "strengths": ["Clear AC"],
            "weaknesses": ["None"],
            "recommendations": ["Proceed"],
            "detailed_scores": {"clarity": 90},
        },
        jira_link="https://jira.example/browse/PROJ-123",
    )

    assert "<h1>PROJ-123: Add login audit trail</h1>" in html_content
    assert "<li>Every login event is recorded</li>" in html_content
    assert "<strong>Overall Score:</strong> 90/100" in html_content
    assert "<li><strong>Clarity:</strong> 90/100</li>" in html_content
