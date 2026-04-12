"""Shared application service for Jira requirement workflow orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.adapters.confluence.direct_confluence_page_adapter import (
    DirectConfluencePageAdapter,
)
from src.adapters.evaluation.jira_evaluation_adapter import JiraEvaluationAdapter
from src.adapters.jira.direct_jira_issue_adapter import DirectJiraIssueAdapter
from src.agent.requirement_workflow import (
    build_backlog_generation_prompt,
    build_requirement_context,
    format_confluence_content,
)
from src.services.rag_ingestion_service import RagIngestionService
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
    workflow_progress: Optional[List[Dict[str, Any]]] = None


class RequirementWorkflowService:
    """Coordinate backlog generation, Jira creation, evaluation, and Confluence page creation."""

    def __init__(
        self,
        llm_provider: Any,
        jira_issue_port: Optional[Any] = None,
        jira_evaluation_port: Optional[Any] = None,
        confluence_page_port: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        jira_tool: Optional[Any] = None,
        jira_evaluator: Optional[Any] = None,
        confluence_tool: Optional[Any] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.jira_issue_port = jira_issue_port or (
            DirectJiraIssueAdapter(jira_tool) if jira_tool else None
        )
        self.jira_evaluation_port = jira_evaluation_port or (
            JiraEvaluationAdapter(jira_evaluator) if jira_evaluator else None
        )
        self.confluence_page_port = confluence_page_port or (
            DirectConfluencePageAdapter(confluence_tool) if confluence_tool else None
        )
        self.rag_ingestion_service = RagIngestionService(rag_service=rag_service)

    def _normalize_port_result(self, result: Any) -> Dict[str, Any]:
        """Accept DTOs, namespaces, or dicts during the Phase 3 transition."""
        if result is None:
            return {}
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if isinstance(result, dict):
            return result

        payload = {}
        for field_name in ("success", "key", "link", "error", "tool_used", "title", "page_id", "raw_result"):
            if hasattr(result, field_name):
                payload[field_name] = getattr(result, field_name)

        raw_result = payload.get("raw_result")
        if isinstance(raw_result, dict):
            normalized_raw_result = dict(raw_result)
            if payload.get("tool_used") is not None:
                normalized_raw_result.setdefault("tool_used", payload["tool_used"])
            if payload.get("title") is not None:
                normalized_raw_result.setdefault("title", payload["title"])
            if payload.get("page_id") is not None:
                normalized_raw_result.setdefault("id", payload["page_id"])
            return normalized_raw_result

        normalized = {}

        normalized.setdefault("success", payload.get("success", False))
        if payload.get("key") is not None:
            normalized.setdefault("key", payload["key"])
        if payload.get("link") is not None:
            normalized.setdefault("link", payload["link"])
        if payload.get("error") is not None:
            normalized.setdefault("error", payload["error"])
        if payload.get("title") is not None:
            normalized.setdefault("title", payload["title"])
        if payload.get("page_id") is not None:
            normalized.setdefault("id", payload["page_id"])
        return normalized

    def _legacy_result_payload(self, result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Preserve the older execute() payload shape while agent callers keep richer data."""
        if result is None:
            return None
        return {key: value for key, value in result.items() if key != "tool_used"}

    def _initial_workflow_progress(self) -> List[Dict[str, Any]]:
        return [
            {"step": "jira", "label": "Create Jira", "status": "skipped"},
            {"step": "evaluation", "label": "Evaluate Requirement", "status": "skipped"},
            {"step": "confluence", "label": "Create Confluence Page", "status": "skipped"},
            {"step": "rag", "label": "Ingest to RAG", "status": "skipped"},
        ]

    @staticmethod
    def _set_progress_status(
        progress: List[Dict[str, Any]],
        step: str,
        status: str,
        detail: Optional[str] = None,
        link: Optional[str] = None,
    ) -> None:
        for item in progress:
            if item["step"] != step:
                continue
            item["status"] = status
            if detail is not None:
                item["detail"] = detail
            if link is not None:
                item["link"] = link
            break

    def _validate_jira_result(self, jira_result: Dict[str, Any]) -> Optional[str]:
        if not jira_result.get("success"):
            return jira_result.get("error", "Unknown error")
        if not jira_result.get("key") or not jira_result.get("link"):
            return "Jira issue creation succeeded but returned no issue key or link."
        return None

    def _validate_evaluation_result(self, evaluation_result: Dict[str, Any]) -> Optional[str]:
        if not isinstance(evaluation_result, dict):
            return "Jira evaluation returned an incomplete result."
        if "overall_maturity_score" not in evaluation_result:
            return "Jira evaluation returned an incomplete result."
        return None

    @staticmethod
    def _build_rag_metadata(
        *,
        issue_key: str,
        page_title: str,
        confluence_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "type": "confluence_page",
            "title": page_title,
            "related_jira": issue_key,
            "link": confluence_result.get("link", ""),
            "page_id": confluence_result.get("id", ""),
        }

    def _ingest_confluence_to_rag(
        self,
        *,
        issue_key: str,
        backlog_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        confluence_result: Dict[str, Any],
    ) -> Optional[str]:
        if not getattr(self.rag_ingestion_service, "rag_service", None):
            return None

        page_title = f"{issue_key}: {backlog_data.get('summary', 'Untitled')}"
        simplified_content = self.rag_ingestion_service.simplify_confluence_content(
            issue_key=issue_key,
            backlog_data=backlog_data,
            evaluation=evaluation_result if evaluation_result else {},
            confluence_link=confluence_result.get("link", ""),
        )
        metadata = self._build_rag_metadata(
            issue_key=issue_key,
            page_title=page_title,
            confluence_result=confluence_result,
        )
        return self.rag_ingestion_service.ingest(simplified_content, metadata)

    def _generate_llm_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        """Support both provider-style and LangChain-style LLM dependencies."""
        invoke = getattr(self.llm_provider, "invoke", None)
        if callable(invoke):
            response = invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = getattr(response, "content", None)
            if isinstance(content, (str, bytes, bytearray)):
                return content.decode() if isinstance(content, (bytes, bytearray)) else content
            if isinstance(response, (str, bytes, bytearray)):
                return response.decode() if isinstance(response, (bytes, bytearray)) else response
            if content is not None:
                return str(content)
            return str(response)

        generate_response = getattr(self.llm_provider, "generate_response", None)
        if callable(generate_response):
            response = generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=json_mode,
            )
            return response.decode() if isinstance(response, (bytes, bytearray)) else response

        raise ValueError("Configured llm_provider does not support generate_response or invoke")

    def _generate_legacy_llm_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        """Preserve the legacy execute() provider preference order."""
        generate_response = getattr(self.llm_provider, "generate_response", None)
        if callable(generate_response):
            response = generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=json_mode,
            )
            return response.decode() if isinstance(response, (bytes, bytearray)) else response

        invoke = getattr(self.llm_provider, "invoke", None)
        if callable(invoke):
            response = invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = getattr(response, "content", None)
            if isinstance(content, (str, bytes, bytearray)):
                return content.decode() if isinstance(content, (bytes, bytearray)) else content
            if isinstance(response, (str, bytes, bytearray)):
                return response.decode() if isinstance(response, (bytes, bytearray)) else response
            if content is not None:
                return str(content)
            return str(response)

        raise ValueError("Configured llm_provider does not support generate_response or invoke")

    def generate_backlog_data_for_agent(
        self,
        *,
        user_input: str,
        messages: List[Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate backlog JSON from the agent's message/history context."""
        context_text = build_requirement_context(
            messages=messages[-6:],
            conversation_history=conversation_history[-5:],
        )
        prompt = build_backlog_generation_prompt(
            context_text=context_text,
            user_input=user_input,
        )
        response = self._generate_llm_response(
            system_prompt="You are a Jira Product Owner assistant. Always respond with valid JSON.",
            user_prompt=prompt,
            json_mode=True,
        )
        return json.loads(self._strip_json_fences(response))

    def create_jira_issue(self, backlog_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Jira issue and normalize the result for all callers."""
        if not self.jira_issue_port:
            return {
                "success": False,
                "error": "Jira tool is not configured. Please check your Jira credentials.",
            }
        return self._normalize_port_result(self.jira_issue_port.create_issue(backlog_data))

    def evaluate_issue(self, issue_key: str) -> Dict[str, Any]:
        """Evaluate a Jira issue through the configured evaluation port."""
        if not self.jira_evaluation_port:
            return {"error": "Jira evaluator is not configured."}
        return self.jira_evaluation_port.evaluate_issue(issue_key)

    def create_confluence_page(
        self,
        *,
        issue_key: str,
        backlog_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        jira_link: str,
    ) -> Dict[str, Any]:
        """Create the lifecycle's Confluence page and normalize the result."""
        if not self.confluence_page_port:
            return {"success": False, "error": "Confluence tool is not configured."}
        confluence_result = self._create_confluence_page(
            issue_key=issue_key,
            backlog_data=backlog_data,
            evaluation_result=evaluation_result,
            jira_link=jira_link,
        )
        return self._normalize_port_result(confluence_result)

    def format_evaluation_result(self, evaluation_result: Dict[str, Any]) -> str:
        """Expose evaluation formatting for agent/chat surfaces."""
        return self._format_evaluation_result(evaluation_result)

    def execute_backlog_data(
        self,
        backlog_data: Dict[str, Any],
    ) -> RequirementWorkflowResult:
        """Run the workflow from an already-approved backlog draft."""
        workflow_progress = self._initial_workflow_progress()

        if not self.jira_issue_port:
            self._set_progress_status(
                workflow_progress,
                "jira",
                "failed",
                detail="Jira tool is not configured. Please check your Jira credentials.",
            )
            return RequirementWorkflowResult(
                success=False,
                response_text=(
                    "I apologize, but the Jira tool is not configured correctly. "
                    "Please check your Jira credentials."
                ),
                backlog_data=backlog_data,
                workflow_progress=workflow_progress,
            )

        try:
            jira_result_payload = self.create_jira_issue(backlog_data)
        except Exception as error:
            logger.error(f"Error during Jira creation: {error}", exc_info=True)
            self._set_progress_status(
                workflow_progress,
                "jira",
                "failed",
                detail=str(error),
            )
            return RequirementWorkflowResult(
                success=False,
                response_text=f"Failed to create Jira issue: {error}",
                backlog_data=backlog_data,
                workflow_progress=workflow_progress,
            )

        jira_validation_error = self._validate_jira_result(jira_result_payload)
        if jira_validation_error:
            self._set_progress_status(
                workflow_progress,
                "jira",
                "failed",
                detail=jira_validation_error,
            )
            return RequirementWorkflowResult(
                success=False,
                response_text=f"Failed to create Jira issue: {jira_validation_error}",
                backlog_data=backlog_data,
                jira_result=self._legacy_result_payload(jira_result_payload),
                workflow_progress=workflow_progress,
            )

        issue_key = jira_result_payload.get("key")
        response_parts = [self._format_jira_success(jira_result_payload, backlog_data)]
        evaluation_result = None
        confluence_result = None

        self._set_progress_status(
            workflow_progress,
            "jira",
            "completed",
            link=jira_result_payload.get("link"),
        )

        if self.jira_evaluation_port:
            try:
                logger.info(f"Evaluating maturity for {issue_key}...")
                evaluation_result = self.evaluate_issue(issue_key)

                evaluation_validation_error = self._validate_evaluation_result(evaluation_result)
                if not evaluation_validation_error:
                    self._set_progress_status(
                        workflow_progress,
                        "evaluation",
                        "completed",
                    )
                    response_parts.append(self.format_evaluation_result(evaluation_result))

                    if self.confluence_page_port:
                        try:
                            confluence_result = self.create_confluence_page(
                                issue_key=issue_key,
                                backlog_data=backlog_data,
                                evaluation_result=evaluation_result,
                                jira_link=jira_result_payload.get("link"),
                            )
                            if confluence_result.get("success"):
                                self._set_progress_status(
                                    workflow_progress,
                                    "confluence",
                                    "completed",
                                    link=confluence_result.get("link"),
                                )
                                rag_document_id = self._ingest_confluence_to_rag(
                                    issue_key=issue_key,
                                    backlog_data=backlog_data,
                                    evaluation_result=evaluation_result,
                                    confluence_result=confluence_result,
                                )
                                if getattr(self.rag_ingestion_service, "rag_service", None):
                                    if rag_document_id:
                                        self._set_progress_status(
                                            workflow_progress,
                                            "rag",
                                            "completed",
                                            detail=rag_document_id,
                                        )
                                    else:
                                        self._set_progress_status(
                                            workflow_progress,
                                            "rag",
                                            "failed",
                                            detail="RAG ingestion did not return a document id.",
                                        )
                            else:
                                self._set_progress_status(
                                    workflow_progress,
                                    "confluence",
                                    "failed",
                                    detail=confluence_result.get("error", "Unknown error"),
                                )
                            response_parts.append(
                                self._format_confluence_result(confluence_result)
                            )
                        except Exception as error:
                            logger.error(f"Error during confluence creation: {error}", exc_info=True)
                            self._set_progress_status(
                                workflow_progress,
                                "confluence",
                                "failed",
                                detail=str(error),
                            )
                            response_parts.append(f"Confluence page creation failed: {error}\n")
                else:
                    self._set_progress_status(
                        workflow_progress,
                        "evaluation",
                        "failed",
                        detail=evaluation_validation_error or evaluation_result.get("error", "Unknown error"),
                    )
                    response_parts.append(
                        "Could not evaluate maturity: "
                        f"{evaluation_validation_error or evaluation_result.get('error', 'Unknown error')}\n"
                    )
            except Exception as error:
                logger.error(f"Error during requirement evaluation: {error}", exc_info=True)
                self._set_progress_status(
                    workflow_progress,
                    "evaluation",
                    "failed",
                    detail=str(error),
                )
                response_parts.append(f"Maturity evaluation failed: {error}\n")

        return RequirementWorkflowResult(
            success=True,
            response_text="".join(response_parts),
            backlog_data=backlog_data,
            jira_result=self._legacy_result_payload(jira_result_payload),
            evaluation_result=evaluation_result,
            confluence_result=self._legacy_result_payload(confluence_result),
            workflow_progress=workflow_progress,
        )

    def execute(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> RequirementWorkflowResult:
        """Run the end-to-end AI requirement workflow and return a rendered response."""
        try:
            backlog_data = self._generate_backlog_data(
                user_input=user_input,
                conversation_history=conversation_history or [],
            )
            return self.execute_backlog_data(backlog_data)
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
        response = self._generate_legacy_llm_response(
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

    def _create_confluence_page(
        self,
        issue_key: str,
        backlog_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        jira_link: str,
    ) -> Any:
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
        return self.confluence_page_port.create_page(
            f"{issue_key}: {backlog_data.get('summary')}",
            confluence_content,
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
            title = confluence_result.get("title")
            response_text = "\n**Confluence Page Created:**\n"
            if title:
                response_text += f"Title: {title}\n"
            response_text += f"Link: {confluence_result.get('link', 'Unknown link')}\n"
            return response_text

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
        return format_confluence_content(
            issue_key=issue_key,
            backlog_data={
                "summary": summary,
                "business_value": business_value,
                "acceptance_criteria": acceptance_criteria,
                "priority": priority,
                "invest_analysis": invest_analysis,
            },
            evaluation=evaluation,
            jira_link=jira_link,
        )
