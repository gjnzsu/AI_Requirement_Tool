import importlib


def test_gateway_provider_available_after_llm_router_import():
    router_module = importlib.import_module("src.llm.router")

    from config.config import Config

    original_gateway_enabled = Config.GATEWAY_ENABLED
    original_gateway_base_url = Config.GATEWAY_BASE_URL
    try:
        Config.GATEWAY_ENABLED = True
        Config.GATEWAY_BASE_URL = "http://ai-gateway-kong.ai-gateway.svc.cluster.local/v1"
        provider = router_module.LLMRouter.get_gateway_provider(
            model="deepseek-v4-flash",
            provider="deepseek",
        )
    finally:
        Config.GATEWAY_ENABLED = original_gateway_enabled
        Config.GATEWAY_BASE_URL = original_gateway_base_url

    assert provider is not None
    assert router_module.GATEWAY_AVAILABLE is True
    assert provider.model == "deepseek-v4-flash"
    assert provider.provider == "deepseek"
