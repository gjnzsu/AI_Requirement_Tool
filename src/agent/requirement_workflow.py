"""Focused helpers for requirement workflow nodes in ChatbotAgent."""

from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


def build_requirement_context(
    messages: List[BaseMessage],
    conversation_history: List[Dict[str, str]],
) -> str:
    """Build compact context text from recent graph messages and prior history."""
    context_lines = []
    for message in messages:
        if isinstance(message, HumanMessage):
            context_lines.append(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            context_lines.append(f"Assistant: {message.content}")

    context_text = "\n".join(context_lines)
    if conversation_history:
        if context_text:
            context_text += "\n\n"
        context_text += "Conversation History:\n"
        for history_message in conversation_history:
            context_text += (
                f"{history_message.get('role', 'user')}: "
                f"{history_message.get('content', '')}\n"
            )

    return context_text


def build_backlog_generation_prompt(context_text: str, user_input: str) -> str:
    """Build the Jira backlog generation prompt for requirement creation."""
    return f"""
        Based on the conversation context below, create a comprehensive Jira backlog item.

        CONTEXT:
        {context_text}

        User request: {user_input}

        REQUIREMENTS:
        1. Summary: Concise title
        2. Business Value: Why this is important
        3. Acceptance Criteria: List of verifiable criteria
        4. Priority: High, Medium, or Low (infer from context, default to Medium)
        5. INVEST Analysis: Brief check against INVEST principles

        OUTPUT FORMAT (JSON):
        {{
            "summary": "...",
            "business_value": "...",
            "acceptance_criteria": ["...", "..."],
            "priority": "...",
            "invest_analysis": "...",
            "description": "..."
        }}

        The 'description' field should combine Business Value, AC, and INVEST analysis.
        """


def format_confluence_content(
    issue_key: str,
    backlog_data: Dict[str, Any],
    evaluation: Dict[str, Any],
    jira_link: str,
) -> str:
    """Format requirement details and maturity output as Confluence HTML."""
    html_parts = [
        f"<h1>{issue_key}: {backlog_data.get('summary', 'Untitled')}</h1>",
        f"<p><strong>Jira Link:</strong> <a href=\"{jira_link}\">{jira_link}</a></p>",
        f"<p><strong>Priority:</strong> {backlog_data.get('priority', 'Not specified')}</p>",
        "<h2>Business Value</h2>",
        f"<p>{backlog_data.get('business_value', 'N/A')}</p>",
    ]

    acceptance_criteria = backlog_data.get("acceptance_criteria", [])
    if acceptance_criteria:
        html_parts.append("<h2>Acceptance Criteria</h2>")
        html_parts.append("<ul>")
        for acceptance_criterion in acceptance_criteria:
            html_parts.append(f"<li>{acceptance_criterion}</li>")
        html_parts.append("</ul>")

    invest_analysis = backlog_data.get("invest_analysis", "")
    if invest_analysis:
        html_parts.append("<h2>INVEST Analysis</h2>")
        html_parts.append(f"<p>{invest_analysis}</p>")

    if evaluation and "overall_maturity_score" in evaluation:
        html_parts.append("<h2>Maturity Evaluation</h2>")
        html_parts.append(
            f"<p><strong>Overall Score:</strong> {evaluation['overall_maturity_score']}/100</p>"
        )

        if evaluation.get("strengths"):
            html_parts.append("<h3>Strengths</h3>")
            html_parts.append("<ul>")
            for strength in evaluation["strengths"]:
                html_parts.append(f"<li>{strength}</li>")
            html_parts.append("</ul>")

        if evaluation.get("weaknesses"):
            html_parts.append("<h3>Areas for Improvement</h3>")
            html_parts.append("<ul>")
            for weakness in evaluation["weaknesses"]:
                html_parts.append(f"<li>{weakness}</li>")
            html_parts.append("</ul>")

        if evaluation.get("recommendations"):
            html_parts.append("<h3>Recommendations</h3>")
            html_parts.append("<ul>")
            for recommendation in evaluation["recommendations"]:
                html_parts.append(f"<li>{recommendation}</li>")
            html_parts.append("</ul>")

        if evaluation.get("detailed_scores"):
            html_parts.append("<h3>Detailed Scores</h3>")
            html_parts.append("<ul>")
            for criterion, score in evaluation["detailed_scores"].items():
                criterion_name = criterion.replace("_", " ").title()
                html_parts.append(
                    f"<li><strong>{criterion_name}:</strong> {score}/100</li>"
                )
            html_parts.append("</ul>")

    return "\n".join(html_parts)
