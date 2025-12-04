"""
Example usage of the Jira Maturity Evaluator Service.

This script demonstrates how to use the service programmatically.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from config.config import Config


def example_basic_usage():
    """Basic example of using the evaluator."""
    
    # Initialize evaluator
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        openai_api_key=Config.OPENAI_API_KEY,
        project_key=Config.JIRA_PROJECT_KEY
    )
    
    # Evaluate a single issue
    backlog_items = evaluator.fetch_backlog_items(max_results=5)
    
    if backlog_items:
        first_item = backlog_items[0]
        result = evaluator.evaluate_maturity(first_item)
        
        print(f"Issue: {result['issue_key']}")
        print(f"Maturity Score: {result['overall_maturity_score']}/100")
        print(f"Recommendations: {result.get('recommendations', [])}")


def example_batch_evaluation():
    """Example of batch evaluating multiple issues."""
    
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        openai_api_key=Config.OPENAI_API_KEY,
        project_key=Config.JIRA_PROJECT_KEY
    )
    
    # Evaluate entire backlog
    results = evaluator.evaluate_backlog(max_items=10)
    
    # Filter high-maturity items
    high_maturity = [r for r in results if r['overall_maturity_score'] >= 80]
    
    print(f"Found {len(high_maturity)} high-maturity items (score >= 80)")
    for item in high_maturity:
        print(f"  - {item['issue_key']}: {item['overall_maturity_score']}/100")


def example_custom_criteria():
    """Example of customizing evaluation criteria."""
    
    evaluator = JiraMaturityEvaluator(
        jira_url=Config.JIRA_URL,
        jira_email=Config.JIRA_EMAIL,
        jira_api_token=Config.JIRA_API_TOKEN,
        openai_api_key=Config.OPENAI_API_KEY,
        project_key=Config.JIRA_PROJECT_KEY
    )
    
    # Add custom criteria
    evaluator.maturity_criteria['test_coverage'] = "Is test coverage plan defined?"
    evaluator.maturity_criteria['documentation'] = "Is documentation plan included?"
    
    # Now evaluations will include these criteria
    results = evaluator.evaluate_backlog(max_items=5)
    
    for result in results:
        print(f"{result['issue_key']}: {result['overall_maturity_score']}/100")


if __name__ == "__main__":
    print("Example 1: Basic Usage")
    print("-" * 50)
    # example_basic_usage()
    
    print("\nExample 2: Batch Evaluation")
    print("-" * 50)
    # example_batch_evaluation()
    
    print("\nExample 3: Custom Criteria")
    print("-" * 50)
    # example_custom_criteria()
    
    print("\nUncomment the examples above to run them.")

