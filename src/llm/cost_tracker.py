"""LLM token cost tracking utilities."""

# Cost per 1K tokens in USD — update as pricing changes
COST_PER_1K_TOKENS = {
    'openai': {
        'gpt-3.5-turbo':  {'prompt': 0.0005,  'completion': 0.0015},
        'gpt-4':          {'prompt': 0.03,    'completion': 0.06},
        'gpt-4o':         {'prompt': 0.005,   'completion': 0.015},
        'gpt-4o-mini':    {'prompt': 0.00015, 'completion': 0.0006},
        'default':        {'prompt': 0.0005,  'completion': 0.0015},
    },
    'gemini': {
        'gemini-pro':     {'prompt': 0.0005,  'completion': 0.0015},
        'default':        {'prompt': 0.0005,  'completion': 0.0015},
    },
    'deepseek': {
        'deepseek-chat':  {'prompt': 0.00014, 'completion': 0.00028},
        'default':        {'prompt': 0.00014, 'completion': 0.00028},
    },
    'coze': {
        'default':        {'prompt': 0.0,     'completion': 0.0},
    },
}


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated USD cost for a given token usage."""
    provider_rates = COST_PER_1K_TOKENS.get(provider, {})
    rates = provider_rates.get(model) or provider_rates.get('default') or {'prompt': 0.0, 'completion': 0.0}
    cost = (prompt_tokens / 1000.0) * rates['prompt'] + (completion_tokens / 1000.0) * rates['completion']
    return round(cost, 8)
