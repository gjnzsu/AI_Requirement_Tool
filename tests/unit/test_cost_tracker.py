import pytest

from src.llm.cost_tracker import COST_PER_1M_TOKENS, calculate_cost


def test_gpt_55_has_explicit_rate_entry():
    assert COST_PER_1M_TOKENS["openai"]["gpt-5.5"] == {
        "prompt": 5.0,
        "completion": 30.0,
    }


def test_gpt_55_cost_uses_per_million_token_pricing():
    cost = calculate_cost(
        "openai",
        "gpt-5.5",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == pytest.approx(35.0)


def test_deepseek_v4_flash_has_explicit_rate_entry():
    assert COST_PER_1M_TOKENS["deepseek"]["deepseek-v4-flash"] == {
        "prompt": 0.14,
        "completion": 0.28,
    }


def test_deepseek_v4_flash_cost_uses_per_million_token_pricing():
    cost = calculate_cost(
        "deepseek",
        "deepseek-v4-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == pytest.approx(0.42)
