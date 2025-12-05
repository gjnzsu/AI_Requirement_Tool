"""
Example usage of multiple LLM providers with the Jira Maturity Evaluator.

This demonstrates how to use different LLM providers (OpenAI, Gemini, DeepSeek).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.llm import LLMRouter
from config.config import Config


def example_openai():
    """Example using OpenAI provider."""
    print("=" * 80)
    print("Example 1: Using OpenAI Provider")
    print("=" * 80)
    
    llm_provider = LLMRouter.get_provider(
        provider_name="openai",
        api_key=Config.OPENAI_API_KEY,
        model="gpt-3.5-turbo"
    )
    
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        project_key=Config.JIRA_PROJECT_KEY,
        llm_provider=llm_provider
    )
    
    # Fetch and evaluate one item
    items = evaluator.fetch_backlog_items(max_results=1)
    if items:
        result = evaluator.evaluate_maturity(items[0])
        print(f"Issue: {result['issue_key']}")
        print(f"Score: {result['overall_maturity_score']}/100")


def example_gemini():
    """Example using Gemini provider."""
    print("\n" + "=" * 80)
    print("Example 2: Using Gemini Provider")
    print("=" * 80)
    
    if not Config.GEMINI_API_KEY:
        print("GEMINI_API_KEY not set. Skipping Gemini example.")
        return
    
    llm_provider = LLMRouter.get_provider(
        provider_name="gemini",
        api_key=Config.GEMINI_API_KEY,
        model="gemini-pro"
    )
    
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        project_key=Config.JIRA_PROJECT_KEY,
        llm_provider=llm_provider
    )
    
    # Fetch and evaluate one item
    items = evaluator.fetch_backlog_items(max_results=1)
    if items:
        result = evaluator.evaluate_maturity(items[0])
        print(f"Issue: {result['issue_key']}")
        print(f"Score: {result['overall_maturity_score']}/100")


def example_deepseek():
    """Example using DeepSeek provider."""
    print("\n" + "=" * 80)
    print("Example 3: Using DeepSeek Provider")
    print("=" * 80)
    
    if not Config.DEEPSEEK_API_KEY:
        print("DEEPSEEK_API_KEY not set. Skipping DeepSeek example.")
        return
    
    llm_provider = LLMRouter.get_provider(
        provider_name="deepseek",
        api_key=Config.DEEPSEEK_API_KEY,
        model="deepseek-chat"
    )
    
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        project_key=Config.JIRA_PROJECT_KEY,
        llm_provider=llm_provider
    )
    
    # Fetch and evaluate one item
    items = evaluator.fetch_backlog_items(max_results=1)
    if items:
        result = evaluator.evaluate_maturity(items[0])
        print(f"Issue: {result['issue_key']}")
        print(f"Score: {result['overall_maturity_score']}/100")


def example_fallback():
    """Example using provider manager with fallback."""
    print("\n" + "=" * 80)
    print("Example 4: Using Provider Manager with Fallback")
    print("=" * 80)
    
    from src.llm import LLMProviderManager
    
    # Create primary and fallback providers
    primary = LLMRouter.get_provider(
        provider_name="openai",
        api_key=Config.OPENAI_API_KEY,
        model="gpt-3.5-turbo"
    )
    
    fallback = None
    if Config.GEMINI_API_KEY:
        fallback = LLMRouter.get_provider(
            provider_name="gemini",
            api_key=Config.GEMINI_API_KEY,
            model="gemini-pro"
        )
    
    # Create provider manager
    provider_manager = LLMProviderManager(
        primary_provider=primary,
        fallback_providers=[fallback] if fallback else []
    )
    
    # Use the manager (will automatically fallback if primary fails)
    system_prompt = "You are a helpful assistant."
    user_prompt = "Say hello in JSON format: {\"greeting\": \"...\"}"
    
    try:
        response = provider_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"All providers failed: {e}")


if __name__ == "__main__":
    print("Multi-Provider LLM Examples")
    print("=" * 80)
    print("\nAvailable providers:", ", ".join(LLMRouter.list_providers()))
    
    # Uncomment the examples you want to run
    # example_openai()
    # example_gemini()
    # example_deepseek()
    # example_fallback()
    
    print("\nUncomment the examples above to run them.")

