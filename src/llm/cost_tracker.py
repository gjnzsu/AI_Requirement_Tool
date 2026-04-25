"""LLM token cost tracking utilities."""

# Cost per 1M tokens in USD. Update as provider pricing changes.
COST_PER_1M_TOKENS = {
    'openai': {
        'gpt-3.5-turbo': {'prompt': 0.5, 'completion': 1.5},
        'gpt-4': {'prompt': 30.0, 'completion': 60.0},
        'gpt-4o': {'prompt': 5.0, 'completion': 15.0},
        'gpt-4o-mini': {'prompt': 0.15, 'completion': 0.6},
        'default': {'prompt': 0.5, 'completion': 1.5},
    },
    'gemini': {
        'gemini-pro': {'prompt': 0.5, 'completion': 1.5},
        'default': {'prompt': 0.5, 'completion': 1.5},
    },
    'deepseek': {
        # DeepSeek V4 Flash official cache-miss pricing:
        # $0.14 / 1M input tokens, $0.28 / 1M output tokens.
        'deepseek-v4-flash': {'prompt': 0.14, 'completion': 0.28},
        'deepseek-chat': {'prompt': 0.14, 'completion': 0.28},
        'deepseek-reasoner': {'prompt': 0.14, 'completion': 0.28},
        'default': {'prompt': 0.14, 'completion': 0.28},
    },
    'coze': {
        'default': {'prompt': 0.0, 'completion': 0.0},
    },
}


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated USD cost for a given token usage."""
    provider_rates = COST_PER_1M_TOKENS.get(provider, {})
    rates = provider_rates.get(model) or provider_rates.get('default') or {'prompt': 0.0, 'completion': 0.0}
    cost = (prompt_tokens / 1_000_000.0) * rates['prompt'] + (
        completion_tokens / 1_000_000.0
    ) * rates['completion']
    return round(cost, 8)
