"""
Jira Requirement Maturity Evaluator Service

This service connects to Jira, retrieves backlog items, and uses an LLM
to evaluate the maturity score of requirements based on various criteria.
"""

import os
from typing import List, Dict, Optional
from jira import JIRA
from openai import OpenAI
import json


class JiraMaturityEvaluator:
    """
    Service to evaluate requirement maturity scores in Jira backlog using LLM.
    """
    
    def __init__(self, jira_url: str, jira_email: str, jira_api_token: str, 
                 openai_api_key: str, project_key: str, openai_model: str = "gpt-3.5-turbo"):
        """
        Initialize the Jira Maturity Evaluator.
        
        Args:
            jira_url: Jira instance URL (e.g., 'https://yourcompany.atlassian.net')
            jira_email: Email address for Jira authentication
            jira_api_token: Jira API token
            openai_api_key: OpenAI API key for LLM evaluation
            project_key: Jira project key (e.g., 'PROJ')
            openai_model: OpenAI model to use (default: 'gpt-3.5-turbo')
                          Options: 'gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview', etc.
        """
        self.jira_url = jira_url
        self.project_key = project_key
        self.openai_model = openai_model
        
        # Initialize Jira client
        self.jira = JIRA(
            server=jira_url,
            basic_auth=(jira_email, jira_api_token)
        )
        
        # Initialize OpenAI client
        self.llm_client = OpenAI(api_key=openai_api_key)
        
        # Maturity evaluation criteria
        self.maturity_criteria = {
            "description_completeness": "How complete and detailed is the requirement description?",
            "acceptance_criteria": "Are clear acceptance criteria defined?",
            "dependencies": "Are dependencies and blockers clearly identified?",
            "business_value": "Is the business value clearly articulated?",
            "technical_feasibility": "Is technical feasibility assessed?",
            "user_story_structure": "Does it follow proper user story format (As a... I want... So that...)?",
            "estimation_readiness": "Is it ready for estimation (story points)?",
            "priority_clarity": "Is priority clearly defined and justified?"
        }
    
    def fetch_backlog_items(self, max_results: int = 50) -> List[Dict]:
        """
        Fetch backlog items from Jira.
        
        Args:
            max_results: Maximum number of items to retrieve
            
        Returns:
            List of dictionaries containing issue information
        """
        try:
            # Query for backlog items (typically in 'To Do' or 'Backlog' status)
            jql = f'project = {self.project_key} AND status IN ("To Do", "Backlog") ORDER BY priority DESC'
            
            issues = self.jira.search_issues(jql, maxResults=max_results, expand='changelog')
            
            backlog_items = []
            for issue in issues:
                item = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': issue.fields.description or '',
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else 'Unassigned',
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'labels': issue.fields.labels,
                    'custom_fields': self._extract_custom_fields(issue)
                }
                backlog_items.append(item)
            
            return backlog_items
            
        except Exception as e:
            print(f"Error fetching backlog items: {str(e)}")
            raise
    
    def _extract_custom_fields(self, issue) -> Dict:
        """Extract custom fields from Jira issue."""
        custom_fields = {}
        for field_name, field_value in issue.raw['fields'].items():
            if field_name.startswith('customfield_'):
                custom_fields[field_name] = field_value
        return custom_fields
    
    def evaluate_maturity(self, issue: Dict) -> Dict:
        """
        Evaluate maturity score for a single requirement using LLM.
        
        Args:
            issue: Dictionary containing issue information
            
        Returns:
            Dictionary with maturity score and detailed evaluation
        """
        # Prepare prompt for LLM evaluation
        prompt = self._create_evaluation_prompt(issue)
        
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.openai_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert requirement analyst. Evaluate requirement maturity based on the provided criteria and return a JSON response with scores (0-100) and explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            }
            
            # JSON mode is supported by gpt-3.5-turbo and gpt-4
            # Add it if the model supports it
            if "gpt-3.5" in self.openai_model or "gpt-4" in self.openai_model:
                api_params["response_format"] = {"type": "json_object"}
            
            # Call LLM for evaluation
            response = self.llm_client.chat.completions.create(**api_params)
            
            # Parse LLM response
            response_content = response.choices[0].message.content.strip()
            
            # Try to extract JSON if response_format wasn't used
            if not response_content.startswith('{'):
                # Try to find JSON in the response
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_content = response_content[start_idx:end_idx]
            
            evaluation_result = json.loads(response_content)
            
            # Calculate overall maturity score (weighted average)
            overall_score = self._calculate_overall_score(evaluation_result)
            
            return {
                'issue_key': issue['key'],
                'overall_maturity_score': overall_score,
                'detailed_scores': evaluation_result.get('scores', {}),
                'recommendations': evaluation_result.get('recommendations', []),
                'strengths': evaluation_result.get('strengths', []),
                'weaknesses': evaluation_result.get('weaknesses', [])
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error evaluating maturity for {issue['key']}: {error_msg}")
            
            # Provide helpful error message for model access issues
            if 'model' in error_msg.lower() and ('not exist' in error_msg.lower() or 'not found' in error_msg.lower()):
                print(f"  → Model '{self.openai_model}' is not available or you don't have access.")
                print(f"  → Try setting OPENAI_MODEL=gpt-3.5-turbo (default) or check your OpenAI account access.")
            
            return {
                'issue_key': issue['key'],
                'overall_maturity_score': 0,
                'error': error_msg
            }
    
    def _create_evaluation_prompt(self, issue: Dict) -> str:
        """Create evaluation prompt for LLM."""
        prompt = f"""
Evaluate the maturity of the following Jira requirement:

Issue Key: {issue['key']}
Summary: {issue['summary']}
Description: {issue['description']}
Status: {issue['status']}
Priority: {issue['priority']}

Evaluation Criteria:
"""
        for criterion, description in self.maturity_criteria.items():
            prompt += f"- {criterion}: {description}\n"
        
        prompt += """
Please provide a JSON response with the following structure:
{
    "scores": {
        "description_completeness": <score 0-100>,
        "acceptance_criteria": <score 0-100>,
        "dependencies": <score 0-100>,
        "business_value": <score 0-100>,
        "technical_feasibility": <score 0-100>,
        "user_story_structure": <score 0-100>,
        "estimation_readiness": <score 0-100>,
        "priority_clarity": <score 0-100>
    },
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...]
}
"""
        return prompt
    
    def _calculate_overall_score(self, evaluation_result: Dict) -> float:
        """Calculate overall maturity score from individual scores."""
        scores = evaluation_result.get('scores', {})
        if not scores:
            return 0.0
        
        # Calculate weighted average (all criteria equally weighted)
        total_score = sum(scores.values())
        return round(total_score / len(scores), 2)
    
    def evaluate_backlog(self, max_items: int = 50) -> List[Dict]:
        """
        Evaluate maturity scores for all backlog items.
        
        Args:
            max_items: Maximum number of items to evaluate
            
        Returns:
            List of evaluation results
        """
        print(f"Fetching backlog items from project {self.project_key}...")
        backlog_items = self.fetch_backlog_items(max_results=max_items)
        
        print(f"Found {len(backlog_items)} items. Evaluating maturity scores...")
        
        evaluation_results = []
        for i, item in enumerate(backlog_items, 1):
            print(f"Evaluating {i}/{len(backlog_items)}: {item['key']}")
            result = self.evaluate_maturity(item)
            evaluation_results.append(result)
        
        return evaluation_results
    
    def update_jira_with_scores(self, evaluation_results: List[Dict], 
                                custom_field_id: Optional[str] = None):
        """
        Update Jira issues with maturity scores.
        
        Args:
            evaluation_results: List of evaluation results
            custom_field_id: Optional custom field ID to store the score
        """
        if not custom_field_id:
            print("No custom field ID provided. Skipping Jira updates.")
            return
        
        for result in evaluation_results:
            try:
                issue = self.jira.issue(result['issue_key'])
                issue.update(fields={custom_field_id: result['overall_maturity_score']})
                print(f"Updated {result['issue_key']} with maturity score: {result['overall_maturity_score']}")
            except Exception as e:
                print(f"Error updating {result['issue_key']}: {str(e)}")

