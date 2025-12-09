"""
Example: Using MCP Integration Utilities for New Tool Integration

This example shows how to use the prevention utilities when integrating
a new MCP service, following best practices to avoid common issues.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp import (
    MCPSchemaValidator,
    MCPContractTester,
    SchemaAwareArgumentBuilder,
    MCPResponseParser
)


def example_integrate_new_mcp_tool():
    """
    Example workflow for integrating a new MCP tool.
    
    This demonstrates the recommended approach to avoid common pitfalls.
    """
    
    # ============================================================
    # STEP 1: Get the tool and schema
    # ============================================================
    print("=" * 60)
    print("STEP 1: Tool Discovery & Schema Retrieval")
    print("=" * 60)
    
    # In real code, this would come from MCP integration
    # For this example, we'll use a sample schema
    tool_name = "createConfluencePage"
    tool_schema = {
        'name': tool_name,
        'description': 'Create a Confluence page',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'cloudId': {
                    'type': 'string',
                    'description': 'Atlassian Cloud ID'
                },
                'spaceId': {
                    'type': 'string',
                    'description': 'Space ID (as string, not number!)'
                },
                'title': {
                    'type': 'string',
                    'description': 'Page title'
                },
                'body': {
                    'type': 'string',
                    'description': 'Page content'
                },
                'contentFormat': {
                    'type': 'string',
                    'enum': ['markdown', 'storage'],
                    'description': 'Content format'
                }
            },
            'required': ['cloudId', 'spaceId', 'title', 'body', 'contentFormat']
        }
    }
    
    # ============================================================
    # STEP 2: Validate Schema Structure
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 2: Schema Validation")
    print("=" * 60)
    
    is_valid, issues = MCPSchemaValidator.validate_schema_structure(tool_schema)
    if not is_valid:
        print(f"❌ Schema validation failed: {issues}")
        return
    
    print("✅ Schema structure is valid")
    
    # ============================================================
    # STEP 3: Analyze Schema
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 3: Schema Analysis")
    print("=" * 60)
    
    MCPSchemaValidator.print_schema_analysis(tool_name, tool_schema)
    
    # ============================================================
    # STEP 4: Build Arguments Using Schema-Aware Builder
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 4: Build Arguments (Schema-Aware)")
    print("=" * 60)
    
    builder = SchemaAwareArgumentBuilder(tool_schema)
    
    # Your internal data format (might be different from tool format)
    internal_data = {
        'title': 'My Page Title',
        'content': '<h1>HTML Content</h1>',  # Your content might be HTML (maps to 'body')
        'body': '<h1>HTML Content</h1>',  # Or use 'body' directly
        'space_key': 'SCRUM',  # You might have space key, not ID
    }
    
    # Context with resolved dependencies
    context = {
        'cloudId': '69fbdc4e-4ae8-4caa-ac51-77f783637203',
        'spaceId': '98307',  # Resolved from space key
        'contentFormat': 'markdown',  # Default format
    }
    
    try:
        # Builder automatically handles:
        # - Parameter name mapping (space_key -> spaceId)
        # - Type conversions
        # - Enum validation
        # - Required parameter checking
        args = builder.build_args(internal_data, context)
        
        print("✅ Arguments built successfully:")
        for key, value in args.items():
            value_str = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
            print(f"   {key}: {value_str} (type: {type(value).__name__})")
            
    except ValueError as e:
        print(f"❌ Argument building failed: {e}")
        return
    
    # ============================================================
    # STEP 5: Contract Testing (Before Tool Call)
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 5: Contract Testing")
    print("=" * 60)
    
    contract_passed = MCPContractTester.generate_test_report(
        tool_name, 
        tool_schema, 
        args
    )
    
    if not contract_passed:
        print("❌ Contract tests failed - fix issues before calling tool")
        return
    
    # ============================================================
    # STEP 6: Call Tool (Simulated)
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 6: Tool Invocation")
    print("=" * 60)
    
    # In real code: result = tool.invoke(input=args)
    # For example, simulating Rovo response format
    mock_response = {
        'id': '720917',
        'spaceId': '98307',
        'title': 'My Page Title',
        'version': {'number': 1},
        '_links': {
            'webui': '/wiki/pages/viewpage.action?pageId=720917'
        }
    }
    
    print(f"📞 Calling tool with args: {list(args.keys())}")
    print(f"📥 Received response (simulated)")
    
    # ============================================================
    # STEP 7: Parse Response
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 7: Response Parsing")
    print("=" * 60)
    
    parser = MCPResponseParser()
    parsed = parser.parse(
        mock_response, 
        expected_format=MCPResponseParser.FORMAT_ROVO
    )
    
    if parsed['success']:
        print(f"✅ Success!")
        print(f"   Page ID: {parsed['id']}")
        print(f"   Title: {parsed.get('title')}")
        print(f"   Link: {parsed.get('link')}")
    else:
        print(f"❌ Failed: {parsed.get('error')}")
    
    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("INTEGRATION SUMMARY")
    print("=" * 60)
    print("✅ Schema validated")
    print("✅ Arguments built with automatic type conversion")
    print("✅ Contract tests passed")
    print("✅ Response parsed correctly")
    print("\nThis tool is ready for production use!")


if __name__ == '__main__':
    example_integrate_new_mcp_tool()

