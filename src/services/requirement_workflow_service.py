"""Shared application service for Jira requirement workflow orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger


logger = get_logger("chatbot.requirement_workflow")


@dataclass
class RequirementWorkflowResult:
    """Structured result for the AI requirement workflow."""

    success: bool
    response_text: str
    backlog_data: Optional[Dict[str, Any]] = None
    jira_result: Optional[Dict[str, Any]] = None
    evaluation_result: Optional[Dict[str, Any]] = None
    confluence_result: Optional[Dict[str, Any]] = None


class RequirementWorkflowService:
    """Coordinate backlog generation, Jira creation, evaluation, and Confluence page creation."""

    def __init__(
        self,
        llm_provider: Any,
        jira_tool: Optional[Any] = None,
        jira_evaluator: Optional[Any] = None,
        confluence_tool: Optional[Any] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.jira_tool = jira_tool
        self.jira_evaluator = jira_evaluator
        self.confluence_tool = confluence_tool

    def execute(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> RequirementWorkflowResult:
        """Run the end-to-end AI requirement workflow and return a rendered response."""
        if not self.jira_tool:
            return RequirementWorkflowResult(
                success=False,
                response_text=(
                    "I apologize, but the Jira tool is not configured correctly. "
                    "Please check your Jira credentials."
                ),
            )

        try:
            backlog_data = self._generate_backlog_data(
                user_input=user_input,
                conversation_history=conversation_history or [],
            )

            jira_result = self.jira_tool.create_issue(
                summary=backlog_data.get("summary"),
                description=backlog_data.get("description"),
                priority=backlog_data.get("priority", "Medium"),
            )

            if not jira_result.get("success"):
                return RequirementWorkflowResult(
                    success=False,
                    response_text=f"Failed to create Jira issue: {jira_result.get('error')}",
                    backlog_data=backlog_data,
                    jira_result=jira_result,
                )

            issue_key = jira_result["key"]
            response_parts = [self._format_jira_success(jira_result, backlog_data)]
            evaluation_result = None
            confluence_result = None

            if self.jira_evaluator:
                try:
                    logger.info(f"Evaluating maturity for {issue_key}...")
                    issue_dict = self._load_created_issue(issue_key)
                    evaluation_result = self.jira_evaluator.evaluate_maturity(issue_dict)

                    if "error" not in evaluation_result:
                        response_parts.append(self._format_evaluation_result(evaluation_result))

                        if self.confluence_tool:
                            confluence_result = self._create_confluence_page(
                                issue_key=issue_key,
                                backlog_data=backlog_data,
                                evaluation_result=evaluation_result,
                                jira_link=jira_result["link"],
                            )
                            response_parts.append(
                                self._format_confluence_result(confluence_result)
                            )
                    else:
                        response_parts.append(
                            "Could not evaluate maturity: "
                            f"{evaluation_result.get('error', 'Unknown error')}\n"
                        )
                except Exception as error:
                    logger.error(f"Error during requirement evaluation: {error}", exc_info=True)
                    response_parts.append(f"Maturity evaluation failed: {error}\n")

            return RequirementWorkflowResult(
                success=True,
                response_text="".join(response_parts),
                backlog_data=backlog_data,
                jira_result=jira_result,
                evaluation_result=evaluation_result,
                confluence_result=confluence_result,
            )
        except Exception as error:
            logger.error(
                f"Error processing Jira creation workflow: {error}",
                exc_info=True,
            )
            return RequirementWorkflowResult(
                success=False,
                response_text=f"Error processing Jira creation request: {error}",
            )

    def _generate_backlog_data(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        context_text = self._format_context(user_input, conversation_history)
        prompt = self._build_generation_prompt(context_text)
        response = self.llm_provider.generate_response(
            system_prompt="You are a Jira Product Owner assistant.",
            user_prompt=prompt,
            json_mode=True,
        )
        return json.loads(self._strip_json_fences(response))

    def _format_context(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        context_lines = [
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in conversation_history
        ]
        context_lines.append(f"user: {user_input}")
        return "\n".join(context_lines)

    def _build_generation_prompt(self, context_text: str) -> str:
        return f"""
        Based on the conversation context below, create a comprehensive Jira backlog item.
        The user's intent is triggered by "create the jira".

        CONTEXT:
        {context_text}

        REQUIREMENTS:
        1. Summary: Concise title
        2. Business Value: Why this is important
        3. Acceptance Criteria: List of verifyable criteria
        4. Priority: High, Medium, or Low (infer from context, default to Medium)
        5. INVEST Analysis: Brief check against INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable)

        OUTPUT FORMAT:
        Provide a valid JSON object with the following keys:
        {{
            "summary": "...",
            "business_value": "...",
            "acceptance_criteria": ["...", "..."],
            "priority": "...",
            "invest_analysis": "...",
            "description": "..."
        }}

        Note: The 'description' field should be a formatted string combining Business Value, AC, and INVEST analysis suitable for the Jira description field.
        """

    def _strip_json_fences(self, response: str) -> str:
        return response.replace("```json", "").replace("```", "").strip()

    def _load_created_issue(self, issue_key: str) -> Dict[str, Any]:
        issue = self.jira_evaluator.jira.issue(issue_key)
        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description or "",
            "status": issue.fields.status.name,
            "priority": (
                issue.fields.priority.name
                if issue.fields.priority
                else "Unassigned"
            ),
        }

    def _create_confluence_page(
        self,
        issue_key: str,
        backlog_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        jira_link: str,
    ) -> Dict[str, Any]:
        logger.info(f"Creating Confluence page for {issue_key}...")
        confluence_content = self.format_confluence_page(
            issue_key=issue_key,
            summary=backlog_data.get("summary"),
            business_value=backlog_data.get("business_value"),
            acceptance_criteria=backlog_data.get("acceptance_criteria", []),
            priority=backlog_data.get("priority"),
            invest_analysis=backlog_data.get("invest_analysis"),
            evaluation=evaluation_result,
            jira_link=jira_link,
        )
        return self.confluence_tool.create_page(
            title=f"{issue_key}: {backlog_data.get('summary')}",
            content=confluence_content,
        )

    def _format_jira_success(
        self,
        jira_result: Dict[str, Any],
        backlog_data: Dict[str, Any],
    ) -> str:
        return (
            f"Successfully created Jira issue: **{jira_result['key']}**\n"
            f"Summary: {backlog_data.get('summary')}\n"
            f"Link: {jira_result['link']}\n\n"
            f"Backlog Details:\n"
            f"- Priority: {backlog_data.get('priority')}\n"
            f"- Business Value: {backlog_data.get('business_value')}\n\n"
        )

    def _format_evaluation_result(self, evaluation_result: Dict[str, Any]) -> str:
        response_text = (
            "Maturity Evaluation Results:\n"
            f"Overall Maturity Score: **{evaluation_result['overall_maturity_score']}/100**\n\n"
        )

        if evaluation_result.get("strengths"):
            response_text += "**Strengths:**\n"
            for strength in evaluation_result["strengths"]:
                response_text += f"  - {strength}\n"
            response_text += "\n"

        if evaluation_result.get("weaknesses"):
            response_text += "**Areas for Improvement:**\n"
            for weakness in evaluation_result["weaknesses"]:
                response_text += f"  - {weakness}\n"
            response_text += "\n"

        if evaluation_result.get("recommendations"):
            response_text += "**Recommendations:**\n"
            for recommendation in evaluation_result["recommendations"]:
                response_text += f"  - {recommendation}\n"
            response_text += "\n"

        if evaluation_result.get("detailed_scores"):
            response_text += "**Detailed Scores:**\n"
            for criterion, score in evaluation_result["detailed_scores"].items():
                criterion_name = criterion.replace("_", " ").title()
                response_text += f"  - {criterion_name}: {score}/100\n"

        return response_text

    def _format_confluence_result(self, confluence_result: Dict[str, Any]) -> str:
        if confluence_result.get("success"):
            return (
                "\n**Confluence Page Created:**\n"
                f"Title: {confluence_result['title']}\n"
                f"Link: {confluence_result['link']}\n"
            )

        error_msg = confluence_result.get("error", "Unknown error")
        return (
            "\n**Confluence page creation failed:**\n"
            f"Error: {error_msg}\n\n"
            "**To enable Confluence page creation, please configure:**\n"
            "- CONFLUENCE_URL in your .env file\n"
            "- CONFLUENCE_SPACE_KEY in your .env file\n"
            "See CONFLUENCE_SETUP.md for details.\n"
        )

    def format_confluence_page(
        self,
        issue_key: str,
        summary: str,
        business_value: str,
        acceptance_criteria: List[str],
        priority: str,
        invest_analysis: str,
        evaluation: Dict[str, Any],
        jira_link: str,
    ) -> str:
        """Format HTML content for a Confluence page."""
        html_content = f"""
<h1>{issue_key}: {summary}</h1>

<h2>Overview</h2>
<p><strong>Jira Issue:</strong> <a href="{jira_link}">{issue_key}</a></p>
<p><strong>Priority:</strong> {priority}</p>

<h2>Business Value</h2>
<p>{business_value}</p>

<h2>Acceptance Criteria</h2>
<ul>
"""
        for acceptance_criterion in acceptance_criteria:
            html_content += f"<li>{acceptance_criterion}</li>\n"

        html_content += "</ul>\n"
        html_content += f"""
<h2>INVEST Analysis</h2>
<p>{invest_analysis}</p>
"""

        if "error" not in evaluation:
            html_content += f"""
<h2>Maturity Evaluation</h2>
<p><strong>Overall Maturity Score: {evaluation['overall_maturity_score']}/100</strong></p>

<h3>Strengths</h3>
<ul>
"""
            for strength in evaluation.get("strengths", []):
                html_content += f"<li>{strength}</li>\n"

            html_content += "</ul>\n"
            html_content += """
<h3>Areas for Improvement</h3>
<ul>
"""
            for weakness in evaluation.get("weaknesses", []):
                html_content += f"<li>{weakness}</li>\n"

            html_content += "</ul>\n"
            html_content += """
<h3>Recommendations</h3>
<ul>
"""
            for recommendation in evaluation.get("recommendations", []):
                html_content += f"<li>{recommendation}</li>\n"

            html_content += "</ul>\n"

            if evaluation.get("detailed_scores"):
                html_content += """
<h3>Detailed Scores</h3>
<table>
<thead>
<tr>
<th>Criterion</th>
<th>Score</th>
</tr>
</thead>
<tbody>
"""
                for criterion, score in evaluation["detailed_scores"].items():
                    criterion_name = criterion.replace("_", " ").title()
                    html_content += (
                        f"<tr><td>{criterion_name}</td><td>{score}/100</td></tr>\n"
                    )

                html_content += """
</tbody>
</table>
"""

        return html_content
