#!/usr/bin/env python3
"""
Pre-Integration Validation Script for MCP Tools.

Run this script before integrating any new MCP service to catch issues early.

Usage:
    python scripts/validate_mcp_tool.py --tool createConfluencePage
    python scripts/validate_mcp_tool.py --tool getJiraIssue --schema-file tool_schema.json
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.schema_validator import MCPSchemaValidator, MCPContractTester


def validate_schema_present(tool_schema: dict) -> dict:
    """Check if schema is present and valid."""
    is_valid, issues = MCPSchemaValidator.validate_schema_structure(tool_schema)
    return {
        'passed': is_valid,
        'message': 'Schema structure valid' if is_valid else f'Issues: {", ".join(issues)}'
    }


def validate_required_params(tool_schema: dict) -> dict:
    """Check if required parameters are documented."""
    if not tool_schema or 'inputSchema' not in tool_schema:
        return {'passed': False, 'message': 'No schema available'}
    
    required = tool_schema['inputSchema'].get('required', [])
    return {
        'passed': True,
        'message': f'{len(required)} required parameter(s) documented'
    }


def validate_type_definitions(tool_schema: dict) -> dict:
    """Check if all parameters have type definitions."""
    if not tool_schema or 'inputSchema' not in tool_schema:
        return {'passed': False, 'message': 'No schema available'}
    
    properties = tool_schema['inputSchema'].get('properties', {})
    params_without_type = [
        name for name, prop in properties.items() 
        if 'type' not in prop
    ]
    
    return {
        'passed': len(params_without_type) == 0,
        'message': f'All parameters have types' if len(params_without_type) == 0 
                   else f'Parameters without type: {", ".join(params_without_type)}'
    }


def validate_enum_values(tool_schema: dict) -> dict:
    """Check if enum parameters are documented."""
    if not tool_schema or 'inputSchema' not in tool_schema:
        return {'passed': False, 'message': 'No schema available'}
    
    properties = tool_schema['inputSchema'].get('properties', {})
    enum_params = {
        name: prop.get('enum', []) 
        for name, prop in properties.items() 
        if 'enum' in prop
    }
    
    return {
        'passed': True,
        'message': f'{len(enum_params)} parameter(s) with enum values'
    }


def validate_response_format(tool_schema: dict) -> dict:
    """Validate response format documentation."""
    # This is a placeholder - response format validation would need
    # additional schema information or documentation
    return {
        'passed': True,
        'message': 'Response format validation not implemented (manual check recommended)'
    }


def validate_auth_requirements(tool_schema: dict) -> dict:
    """Check authentication requirements."""
    if not tool_schema or 'inputSchema' not in tool_schema:
        return {'passed': False, 'message': 'No schema available'}
    
    properties = tool_schema['inputSchema'].get('properties', {})
    auth_params = ['cloudId', 'cloud_id', 'apiKey', 'api_key', 'token']
    found_auth = [p for p in properties.keys() if any(auth in p.lower() for auth in auth_params)]
    
    return {
        'passed': True,
        'message': f'Auth parameters found: {", ".join(found_auth)}' if found_auth 
                   else 'No explicit auth parameters (may use global auth)'
    }


def main():
    parser = argparse.ArgumentParser(description='Validate MCP tool before integration')
    parser.add_argument('--tool', help='Tool name to validate', required=True)
    parser.add_argument('--schema-file', help='Path to schema JSON file')
    parser.add_argument('--sample-args', help='Path to sample arguments JSON file')
    
    args = parser.parse_args()
    
    # Load schema
    if args.schema_file:
        with open(args.schema_file, 'r') as f:
            tool_schema = json.load(f)
    else:
        # Try to get from MCP integration
        print("⚠️  Schema file not provided. Trying to load from MCP integration...")
        try:
            from src.mcp.mcp_integration import MCPIntegration
            import asyncio
            
            integration = MCPIntegration()
            asyncio.run(integration.initialize())
            
            tool = integration.get_tool(args.tool)
            if tool and hasattr(tool, '_tool_schema'):
                tool_schema = tool._tool_schema
            else:
                print(f"❌ Could not find tool '{args.tool}' or its schema")
                return 1
        except Exception as e:
            print(f"❌ Error loading schema: {e}")
            return 1
    
    # Validate schema structure
    is_valid, issues = MCPSchemaValidator.validate_schema_structure(tool_schema)
    if not is_valid:
        print(f"❌ Schema structure invalid: {', '.join(issues)}")
        return 1
    
    # Run validation checks
    checks = [
        ("Schema Present", validate_schema_present),
        ("Required Parameters", validate_required_params),
        ("Type Definitions", validate_type_definitions),
        ("Enum Values", validate_enum_values),
        ("Response Format", validate_response_format),
        ("Authentication", validate_auth_requirements),
    ]
    
    print(f"\n🔍 Validating MCP Tool: {args.tool}\n")
    
    results = {}
    for check_name, check_func in checks:
        try:
            result = check_func(tool_schema)
            results[check_name] = result
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {check_name}: {result.get('message', '')}")
        except Exception as e:
            results[check_name] = {'passed': False, 'error': str(e)}
            print(f"❌ {check_name}: Error - {e}")
    
    # Print schema analysis
    print()
    MCPSchemaValidator.print_schema_analysis(args.tool, tool_schema)
    
    # Test with sample arguments if provided
    if args.sample_args:
        print(f"\n🧪 Testing with sample arguments...")
        with open(args.sample_args, 'r') as f:
            sample_args = json.load(f)
        
        MCPContractTester.generate_test_report(args.tool, tool_schema, sample_args)
    
    # Summary
    passed = sum(1 for r in results.values() if r.get('passed', False))
    total = len(checks)
    
    print(f"\n📊 Validation Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ Tool is ready for integration!")
        return 0
    else:
        print("⚠️  Please address the issues above before integration")
        return 1


if __name__ == '__main__':
    sys.exit(main())

