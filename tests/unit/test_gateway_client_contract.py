import json

import httpx
import pytest

from src.gateway.client.gateway_client import GatewayClient
from src.gateway.providers.gateway_provider_wrapper import GatewayProviderWrapper


@pytest.mark.asyncio
async def test_gateway_client_omits_openai_provider_from_openai_compatible_payload():
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


def test_gateway_client_sync_omits_openai_provider_from_openai_compatible_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.read().decode("utf-8")
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
        provider="openai",
    )
    sync_client.close()

    assert captured["url"] == "http://gateway.example/v1/chat/completions"
    payload = json.loads(captured["json"])
    assert "provider" not in payload
    assert response["choices"][0]["message"]["content"] == "sync ok"


def test_gateway_client_sync_keeps_non_openai_provider_for_gateway_routing():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read().decode("utf-8")
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
        model="deepseek/deepseek-v4-flash",
        provider="deepseek",
    )
    sync_client.close()

    payload = json.loads(captured["json"])
    assert payload["provider"] == "deepseek"
    assert response["choices"][0]["message"]["content"] == "sync ok"


def test_gateway_provider_wrapper_prefixes_deepseek_model_for_litellm():
    captured = {}

    class FakeGatewayClient:
        def chat_completion_sync(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"message": {"content": "ok"}}]}

    provider = GatewayProviderWrapper(
        model="deepseek-v4-flash",
        provider="deepseek",
    )
    provider.gateway_client = FakeGatewayClient()

    response = provider.generate_response(
        system_prompt="system",
        user_prompt="hello",
    )

    assert response == "ok"
    assert captured["model"] == "deepseek/deepseek-v4-flash"
    assert captured["provider"] == "deepseek"
