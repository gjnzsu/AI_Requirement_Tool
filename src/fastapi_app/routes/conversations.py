"""FastAPI conversation routes with Flask contract parity."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from src.fastapi_app.dependencies import authenticate_request, error_response, get_runtime
from src.webapp.conversation_ids import generate_conversation_id

router = APIRouter(tags=["conversations"])


@router.get("/api/conversations")
async def get_conversations(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            conv_list = memory_manager.list_conversations(order_by="updated_at")
            conv_list = [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"],
                    "message_count": conv.get("message_count", 0),
                }
                for conv in conv_list
            ]
        else:
            conv_list = [
                {
                    "id": conv_id,
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "updated_at": conv.get("updated_at", conv["created_at"]),
                    "message_count": len(conv["messages"]),
                }
                for conv_id, conv in conversations.items()
            ]
            conv_list.sort(key=lambda item: item.get("updated_at", item["created_at"]), reverse=True)

        return {"conversations": conv_list}
    except Exception as error:
        return error_response(500, str(error))


@router.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return error_response(404, "Conversation not found")
            return {"conversation": conversation}

        if conversation_id not in conversations:
            return error_response(404, "Conversation not found")

        return {"conversation": conversations[conversation_id]}
    except Exception as error:
        return error_response(500, str(error))


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return error_response(404, "Conversation not found")
            memory_manager.delete_conversation(conversation_id)
        else:
            if conversation_id not in conversations:
                return error_response(404, "Conversation not found")
            del conversations[conversation_id]

        return {"success": True}
    except Exception as error:
        return error_response(500, str(error))


@router.delete("/api/conversations")
async def clear_all_conversations(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        if runtime.memory_manager:
            runtime.memory_manager.delete_all_conversations()
        else:
            runtime.conversations.clear()

        return {"success": True}
    except Exception as error:
        return error_response(500, str(error))


@router.put("/api/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    runtime=Depends(get_runtime),
):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        data = await request.json()
        new_title = str((data or {}).get("title", "")).strip()

        if not new_title:
            return error_response(400, "Title is required")

        if runtime.memory_manager:
            conversation = runtime.memory_manager.get_conversation(conversation_id)
            if not conversation:
                return error_response(404, "Conversation not found")
            runtime.memory_manager.update_conversation_title(conversation_id, new_title)
        else:
            if conversation_id not in runtime.conversations:
                return error_response(404, "Conversation not found")
            runtime.conversations[conversation_id]["title"] = new_title

        return {"success": True, "title": new_title}
    except Exception as error:
        return error_response(500, str(error))


@router.post("/api/new-chat")
async def new_chat(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        conversation_id = generate_conversation_id()

        if runtime.memory_manager:
            runtime.memory_manager.create_conversation(conversation_id, title="New Chat")
        else:
            runtime.conversations[conversation_id] = {
                "messages": [],
                "title": "New Chat",
                "created_at": datetime.now().isoformat(),
            }

        return {"conversation_id": conversation_id, "success": True}
    except Exception as error:
        return error_response(500, str(error))


@router.get("/api/search")
async def search_conversations(
    q: str | None = None,
    limit: str | None = "10",
    authorization: str | None = Header(default=None),
    runtime=Depends(get_runtime),
):
    auth_result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(auth_result, JSONResponse):
        return auth_result

    try:
        query = (q or "").strip()
        if not query:
            return error_response(400, "Search query is required")

        try:
            parsed_limit = int(limit if limit is not None else 10)
        except (TypeError, ValueError):
            return error_response(400, f"Invalid limit: {limit}. Must be an integer.")

        if runtime.memory_manager:
            results = runtime.memory_manager.search_conversations(query, limit=parsed_limit)
            conv_list = [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"],
                    "message_count": conv.get("message_count", 0),
                }
                for conv in results
            ]
        else:
            conv_list = [
                {
                    "id": conv_id,
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "message_count": len(conv["messages"]),
                }
                for conv_id, conv in runtime.conversations.items()
                if query.lower() in conv["title"].lower()
                or any(query.lower() in msg.get("content", "").lower() for msg in conv["messages"])
            ][:parsed_limit]

        return {"conversations": conv_list}
    except Exception as error:
        return error_response(500, str(error))
