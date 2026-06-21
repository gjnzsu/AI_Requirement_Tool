import json

import httpx
import pytest

from src.gateway.client.gateway_client import GatewayClient


@pytest.mark.asyncio
async def test_gateway_client_uses_openai_compatible_payload_and_consumer_header():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["json"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="http://ai-gateway-kong.ai-gateway.svc.cluster.local/v1",
        transport=transport,
    )
    client = GatewayClient(
        base_url="http://ai-gateway-kong.ai-gateway.svc.cluster.local/v1",
        consumer_service="ai-requirement-tool",
        http_client=http_client,
    )

    try:
        await client.chat_completion(
            messages=[{"role": "user", "content": "hello"}],
            model="gpt-5.4",
            provider="openai",
            json_mode=True,
            cache=True,
        )
    finally:
        await http_client.aclose()

    assert captured["url"] == (
        "http://ai-gateway-kong.ai-gateway.svc.cluster.local/v1/chat/completions"
    )
    assert captured["headers"]["x-consumer-service"] == "ai-requirement-tool"
    payload = json.loads(captured["json"])
    assert payload == {
        "messages": [{"role": "user", "content": "hello"}],
        "model": "gpt-5.4",
        "response_format": {"type": "json_object"},
    }


def test_gateway_client_sync_uses_injected_sync_transport():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "sync ok"}}]},
        )

    sync_client = httpx.Client(
        base_url="http://gateway.example/v1",
        transport=httpx.MockTransport(handler),
    )
    client = GatewayClient(
        base_url="http://gateway.example/v1",
        sync_http_client=sync_client,
    )

    response = client.chat_completion_sync(
        messages=[{"role": "user", "content": "hello"}],
        model="gpt-5.4",
    )
    sync_client.close()

    assert captured["url"] == "http://gateway.example/v1/chat/completions"
    assert response["choices"][0]["message"]["content"] == "sync ok"
