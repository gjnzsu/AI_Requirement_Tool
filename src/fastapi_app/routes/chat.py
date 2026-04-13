"""FastAPI chat and model routes with Flask contract parity."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from src.fastapi_app.dependencies import authenticate_request, error_response, get_runtime
from src.webapp.conversation_ids import generate_conversation_id

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(request: Request, authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Send a chat message and return orchestrated response payload."""
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        if request.headers.get("content-type") is None or "application/json" not in request.headers.get("content-type", ""):
            return error_response(400, "Request must be JSON")

        try:
            data = await request.json()
            if data is None:
                return error_response(400, "Invalid JSON in request body")
        except Exception as error:
            return error_response(400, f"Failed to parse JSON: {str(error)}")

        message = str((data or {}).get("message", "")).strip()
        conversation_id = (data or {}).get("conversation_id")
        model = str((data or {}).get("model", "openai")).lower()
        agent_mode = str((data or {}).get("agent_mode", "auto")).lower()

        if not message:
            return error_response(400, "Message is required")

        if model not in ["openai", "gemini", "deepseek"]:
            return error_response(400, f"Invalid model: {model}. Supported models: openai, gemini, deepseek")
        if agent_mode not in ["auto", "requirement_sdlc_agent"]:
            return error_response(
                400,
                f"Invalid agent mode: {agent_mode}. Supported agent modes: auto, requirement_sdlc_agent",
            )

        title = message[:50] + ("..." if len(message) > 50 else "")
        conversation_id = runtime.ensure_conversation(
            conversation_id=conversation_id,
            title=title,
            generator=generate_conversation_id,
            memory_manager=runtime.memory_manager,
        )

        chatbot = runtime.get_chatbot()
        try:
            execution_result = runtime.execute_chat_request(
                message=message,
                conversation_id=conversation_id,
                model=model,
                agent_mode=agent_mode,
                chatbot=chatbot,
                memory_manager=runtime.memory_manager,
            )
        except ValueError as error:
            return error_response(400, str(error))

        if runtime.memory_manager:
            conversation = runtime.memory_manager.get_conversation(conversation_id)
            if conversation and len(conversation.get("messages", [])) == 2:
                runtime.memory_manager.update_conversation_title(conversation_id, title)
        elif conversation_id in runtime.conversations:
            conversation = runtime.conversations[conversation_id]
            if len(conversation.get("messages", [])) == 2:
                conversation["title"] = title

        return {
            "response": execution_result.response,
            "conversation_id": conversation_id,
            "agent_mode": agent_mode,
            "ui_actions": execution_result.ui_actions,
            "workflow_progress": execution_result.workflow_progress,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as error:
        error_type = type(error).__name__
        error_str = str(error).lower()

        http_status_code = None
        if hasattr(error, "status_code"):
            http_status_code = error.status_code
        elif hasattr(error, "response") and hasattr(error.response, "status_code"):
            http_status_code = error.response.status_code
        elif "429" in error_str:
            http_status_code = 429

        is_rate_limit = (
            http_status_code == 429
            or "RateLimit" in error_type
            or "rate limit" in error_str
            or "quota" in error_str
            or "429" in error_str
        )

        if is_rate_limit:
            return error_response(
                429,
                "Rate limit exceeded. The API has received too many requests. "
                "Please wait a few minutes and try again, or switch to a different model.",
            )

        return error_response(500, str(error))


@router.get("/api/current-model")
async def get_current_model(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Return active chatbot provider and available providers."""
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        chatbot = runtime.get_chatbot()
        return {
            "model": chatbot.provider_name,
            "available_models": ["openai", "gemini", "deepseek"],
        }
    except Exception as error:
        return error_response(500, str(error))
