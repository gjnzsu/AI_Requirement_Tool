"""
Generic Response Parser for MCP Tools.

Handles different MCP server response formats and standardizes them
into a common structure for easier processing.
"""

from typing import Dict, Any, Optional, List
import json
import re
from config.config import Config


class MCPResponseParser:
    """Generic response parser for different MCP server formats."""
    
    # Known response format types
    FORMAT_ROVO = 'rovo'  # Rovo MCP Server format: direct object with 'id'
    FORMAT_CUSTOM = 'custom'  # Custom format: object with 'success' flag
    FORMAT_GENERIC = 'generic'  # Generic format: try to infer
    
    def __init__(self, default_format: str = FORMAT_GENERIC):
        """
        Initialize response parser.
        
        Args:
            default_format: Default format to assume if auto-detection fails
        """
        self.default_format = default_format
    
    def parse(self, response: Any, expected_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse MCP tool response into standardized format.
        
        Args:
            response: Raw response from MCP tool (string, dict, etc.)
            expected_format: Expected format (None for auto-detect)
            
        Returns:
            Standardized response dictionary with keys:
            - success: bool
            - id: Optional[str] - resource ID
            - title: Optional[str] - resource title
            - link: Optional[str] - resource URL
            - error: Optional[str] - error message if failed
            - raw_response: Original response for debugging
        """
        # Parse string response to dict
        if isinstance(response, str):
            response = self._parse_string_response(response)
        
        # Handle dict response
        if isinstance(response, dict):
            # Detect format if not specified
            if expected_format is None:
                expected_format = self._detect_format(response)
            
            # Parse based on format
            if expected_format == self.FORMAT_ROVO:
                return self._parse_rovo_format(response)
            elif expected_format == self.FORMAT_CUSTOM:
                return self._parse_custom_format(response)
            else:
                return self._parse_generic_format(response)
        
        # Handle other types
        return {
            'success': False,
            'error': f'Unexpected response type: {type(response).__name__}',
            'raw_response': response
        }
    
    def _parse_string_response(self, response: str) -> Dict[str, Any]:
        """
        Parse string response into dictionary.
        
        Args:
            response: String response
            
        Returns:
            Parsed dictionary
        """
        cleaned = response.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            json_lines = [line for line in lines if not line.strip().startswith('```')]
            cleaned = '\n'.join(json_lines).strip()
        
        # Try direct JSON parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Try regex extraction
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all parsing fails, return error response
        return {
            'success': False,
            'error': 'Could not parse response as JSON',
            'raw_response': response
        }
    
    def _detect_format(self, response: Dict[str, Any]) -> str:
        """
        Auto-detect response format.
        
        Args:
            response: Response dictionary
            
        Returns:
            Detected format string
        """
        # Rovo format: has 'id' but no 'success' flag
        if 'id' in response and 'success' not in response:
            return self.FORMAT_ROVO
        
        # Custom format: has explicit 'success' flag
        if 'success' in response:
            return self.FORMAT_CUSTOM
        
        # Generic: try to infer from structure
        return self.default_format
    
    def _parse_rovo_format(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Rovo MCP Server format.
        
        Rovo format: Direct page/object with 'id' field, no 'success' flag.
        
        Args:
            response: Response dictionary
            
        Returns:
            Standardized response
        """
        # Extract ID from various possible locations
        page_id = (
            response.get('id') or 
            response.get('pageId') or 
            response.get('page_id')
        )
        
        if not page_id:
            # Check nested structures
            if isinstance(response.get('version'), dict):
                page_id = response.get('version', {}).get('id')
        
        if not page_id:
            return {
                'success': False,
                'error': 'No resource ID found in Rovo format response',
                'raw_response': response
            }
        
        # Convert ID to string
        page_id = str(page_id)
        
        # Extract link
        link = self._extract_link(response, page_id)
        
        return {
            'success': True,
            'id': page_id,
            'title': response.get('title'),
            'link': link,
            'raw_response': response
        }
    
    def _parse_custom_format(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse custom MCP server format with explicit success flag.
        
        Args:
            response: Response dictionary
            
        Returns:
            Standardized response
        """
        if response.get('success'):
            return {
                'success': True,
                'id': str(response.get('id') or response.get('page_id') or ''),
                'title': response.get('title'),
                'link': response.get('link') or self._extract_link(response, response.get('id')),
                'raw_response': response
            }
        else:
            return {
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'error_detail': response.get('error_detail'),
                'error_type': response.get('error_type'),
                'raw_response': response
            }
    
    def _parse_generic_format(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse generic format - try to infer success/failure.
        
        Args:
            response: Response dictionary
            
        Returns:
            Standardized response
        """
        # Check for error indicators
        if 'error' in response or 'errorMessage' in response or 'failure' in response:
            return {
                'success': False,
                'error': response.get('error') or response.get('errorMessage') or 'Unknown error',
                'raw_response': response
            }
        
        # Check for success indicators
        if 'id' in response:
            return {
                'success': True,
                'id': str(response.get('id')),
                'title': response.get('title'),
                'link': self._extract_link(response, response.get('id')),
                'raw_response': response
            }
        
        # Ambiguous - assume success if no error indicators
        return {
            'success': True,  # Optimistic interpretation
            'raw_response': response
        }
    
    def _extract_link(self, response: Dict[str, Any], resource_id: Optional[str]) -> Optional[str]:
        """
        Extract resource link from various possible locations.
        
        Args:
            response: Response dictionary
            resource_id: Resource ID for constructing link
            
        Returns:
            Resource URL or None
        """
        # Direct link field
        if response.get('link'):
            return response['link']
        
        # _links structure (HAL format)
        if response.get('_links', {}).get('webui'):
            webui = response['_links']['webui']
            if webui.startswith('http'):
                return webui
            else:
                # Relative URL - construct absolute
                try:
                    base_url = Config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
                    return f"{base_url}{webui}"
                except:
                    pass
        
        # Construct from ID if we have base URL and resource type
        if resource_id:
            # Try to infer resource type from response
            if 'spaceId' in response or 'pageId' in response:
                # Confluence page
                try:
                    base_url = Config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
                    return f"{base_url}/wiki/pages/viewpage.action?pageId={resource_id}"
                except:
                    pass
        
        return None
    
    @staticmethod
    def parse_error_response(response: Any) -> Dict[str, Any]:
        """
        Parse error response from MCP tool.
        
        Args:
            response: Error response (string or dict)
            
        Returns:
            Error information dictionary
        """
        if isinstance(response, str):
            # Check for error prefix
            if response.strip().startswith('Error:'):
                return {
                    'success': False,
                    'error': response.replace('Error:', '').strip(),
                    'raw_response': response
                }
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return {
                        'success': False,
                        'error': parsed.get('error', parsed.get('message', 'Unknown error')),
                        'error_detail': parsed.get('error_detail'),
                        'raw_response': parsed
                    }
            except:
                pass
            
            return {
                'success': False,
                'error': response,
                'raw_response': response
            }
        
        if isinstance(response, dict):
            return {
                'success': False,
                'error': response.get('error', response.get('message', 'Unknown error')),
                'error_detail': response.get('error_detail'),
                'error_type': response.get('error_type'),
                'raw_response': response
            }
        
        return {
            'success': False,
            'error': f'Unexpected error response type: {type(response).__name__}',
            'raw_response': response
        }

