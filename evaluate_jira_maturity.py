"""
Main script to run Jira Requirement Maturity Evaluation Service.

Usage:
    python evaluate_jira_maturity.py
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.llm import LLMRouter
from config.config import Config


def main():
    """Main function to run the maturity evaluation service."""
    
    # Validate configuration
    if not Config.validate():
        print("ERROR: Configuration not set properly.")
        print("\nPlease set the following environment variables:")
        print("\nJira Configuration:")
        print("  - JIRA_URL")
        print("  - JIRA_EMAIL")
        print("  - JIRA_API_TOKEN")
        print("  - JIRA_PROJECT_KEY")
        print("\nLLM Provider Configuration:")
        print("  - LLM_PROVIDER (options: 'openai', 'gemini', 'deepseek')")
        print("\nProvider-specific API keys:")
        print("  - OPENAI_API_KEY (if using OpenAI)")
        print("  - GEMINI_API_KEY (if using Gemini)")
        print("  - DEEPSEEK_API_KEY (if using DeepSeek)")
        print("\nOr update config/config.py with your credentials.")
        print("\nYou can also create a .env file in the project root with these variables.")
        return 1
    
    try:
        # Initialize LLM provider
        provider_name = Config.LLM_PROVIDER
        api_key = Config.get_llm_api_key()
        model = Config.get_llm_model()
        
        # Prepare provider kwargs (e.g., proxy for Gemini)
        provider_kwargs = {}
        if provider_name.lower() == 'gemini':
            # Use GEMINI_PROXY if set, otherwise fall back to HTTP_PROXY/HTTPS_PROXY
            proxy = Config.GEMINI_PROXY or Config.HTTPS_PROXY or Config.HTTP_PROXY
            if proxy:
                provider_kwargs['proxy'] = proxy
                print(f"Using proxy: {proxy}")
        
        print(f"Initializing LLM Provider: {provider_name} (model: {model})...")
        llm_provider = LLMRouter.get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            **provider_kwargs
        )
        
        # Initialize evaluator
        print(f"Initializing Jira Maturity Evaluator...")
        evaluator = JiraMaturityEvaluator(
            jira_url=Config.JIRA_URL,
            jira_email=Config.JIRA_EMAIL,
            jira_api_token=Config.JIRA_API_TOKEN,
            project_key=Config.JIRA_PROJECT_KEY,
            llm_provider=llm_provider
        )
        
        # Evaluate backlog
        results = evaluator.evaluate_backlog(max_items=Config.MAX_BACKLOG_ITEMS)
        
        # Display results
        print("\n" + "="*80)
        print("MATURITY EVALUATION RESULTS")
        print("="*80)
        
        for result in results:
            print(f"\nIssue: {result['issue_key']}")
            print(f"Overall Maturity Score: {result['overall_maturity_score']}/100")
            
            if 'detailed_scores' in result:
                print("\nDetailed Scores:")
                for criterion, score in result['detailed_scores'].items():
                    print(f"  - {criterion.replace('_', ' ').title()}: {score}/100")
            
            if 'strengths' in result and result['strengths']:
                print("\nStrengths:")
                for strength in result['strengths']:
                    print(f"  + {strength}")
            
            if 'weaknesses' in result and result['weaknesses']:
                print("\nWeaknesses:")
                for weakness in result['weaknesses']:
                    print(f"  - {weakness}")
            
            if 'recommendations' in result and result['recommendations']:
                print("\nRecommendations:")
                for rec in result['recommendations']:
                    print(f"  → {rec}")
            
            print("-" * 80)
        
        # Save results to JSON file
        output_file = project_root / 'maturity_evaluation_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
        # Optionally update Jira with scores
        if Config.JIRA_MATURITY_SCORE_FIELD:
            print("\nUpdating Jira issues with maturity scores...")
            evaluator.update_jira_with_scores(results, Config.JIRA_MATURITY_SCORE_FIELD)
        
        # Summary statistics
        if results:
            avg_score = sum(r['overall_maturity_score'] for r in results) / len(results)
            print(f"\nSummary:")
            print(f"  Total items evaluated: {len(results)}")
            print(f"  Average maturity score: {avg_score:.2f}/100")
            print(f"  Highest score: {max(r['overall_maturity_score'] for r in results)}/100")
            print(f"  Lowest score: {min(r['overall_maturity_score'] for r in results)}/100")
        
    except Exception as e:
        print(f"Error running evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

