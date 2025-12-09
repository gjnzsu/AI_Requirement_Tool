# MCP Integration Guide - Prevention Strategies

This guide documents the prevention strategies and utilities we've created to avoid common issues when integrating new MCP services.

## Overview

During the Confluence MCP integration, we encountered 12 different issues. To prevent similar problems in future integrations, we've created reusable utilities and best practices.

## Available Utilities

### 1. Schema Validator (`MCPSchemaValidator`)

Validates and analyzes MCP tool schemas before integration.

**Location**: `src/mcp/schema_validator.py`

**Usage**:
```python
from src.mcp import MCPSchemaValidator

# Validate schema structure
is_valid, issues = MCPSchemaValidator.validate_schema_structure(tool_schema)

# Analyze and print schema
MCPSchemaValidator.print_schema_analysis(tool_name, tool_schema)
```

**Benefits**:
- Catches schema structure issues early
- Provides clear documentation of parameters
- Identifies required vs optional parameters
- Highlights enum values

### 2. Contract Tester (`MCPContractTester`)

Tests contracts between your code and MCP tool schemas.

**Location**: `src/mcp/schema_validator.py`

**Usage**:
```python
from src.mcp import MCPContractTester

# Test before tool call
sample_args = {'cloudId': 'test-123', 'spaceId': '98307', ...}
MCPContractTester.generate_test_report(tool_name, tool_schema, sample_args)

# Or test specific aspects
type_violations = MCPContractTester.test_parameter_types(tool_schema, args)
missing_params = MCPContractTester.test_required_parameters(tool_schema, args)
enum_violations = MCPContractTester.test_enum_values(tool_schema, args)
```

**Benefits**:
- Catches type mismatches before runtime
- Validates enum values
- Ensures required parameters are provided
- Provides detailed violation reports

### 3. Schema-Aware Argument Builder (`SchemaAwareArgumentBuilder`)

Automatically builds arguments with proper type conversion and validation.

**Location**: `src/mcp/argument_builder.py`

**Usage**:
```python
from src.mcp import SchemaAwareArgumentBuilder

builder = SchemaAwareArgumentBuilder(tool_schema)

# Build arguments - handles type conversion, enum validation, etc.
args = builder.build_args(
    data_mapping={
        'title': 'My Title',
        'space_key': 'SCRUM',  # Will map to spaceId
    },
    context={
        'cloudId': cloud_id,
        'spaceId': str(space_id),  # Resolved dependency
        'contentFormat': 'markdown',
    }
)
```

**Benefits**:
- Automatic type conversion (string/int/number/boolean)
- Parameter name mapping (flexible matching)
- Enum validation
- Required parameter checking
- Prevents type mismatch errors

### 4. Response Parser (`MCPResponseParser`)

Handles different MCP server response formats.

**Location**: `src/mcp/response_parser.py`

**Usage**:
```python
from src.mcp import MCPResponseParser

parser = MCPResponseParser()

# Parse response (auto-detects format)
parsed = parser.parse(response)

# Or specify format explicitly
parsed = parser.parse(response, expected_format=MCPResponseParser.FORMAT_ROVO)

if parsed['success']:
    page_id = parsed['id']
    link = parsed['link']
else:
    error = parsed['error']
```

**Benefits**:
- Handles Rovo, Custom, and Generic formats
- Standardizes response structure
- Extracts IDs and links from various locations
- Provides consistent error handling

### 5. Validation Script

Pre-integration validation script.

**Location**: `scripts/validate_mcp_tool.py`

**Usage**:
```bash
# Validate tool before integration
python scripts/validate_mcp_tool.py --tool createConfluencePage

# With schema file
python scripts/validate_mcp_tool.py --tool myTool --schema-file schema.json

# With sample arguments
python scripts/validate_mcp_tool.py --tool myTool --schema-file schema.json --sample-args args.json
```

## Integration Workflow

### Recommended Steps

1. **Discovery**
   ```python
   # Get tool and schema
   tool = mcp_integration.get_tool('toolName')
   tool_schema = tool._tool_schema
   
   # Analyze schema
   MCPSchemaValidator.print_schema_analysis('toolName', tool_schema)
   ```

2. **Validation**
   ```python
   # Validate schema structure
   is_valid, issues = MCPSchemaValidator.validate_schema_structure(tool_schema)
   
   # Run validation script
   # python scripts/validate_mcp_tool.py --tool toolName
   ```

3. **Implementation**
   ```python
   # Use argument builder
   builder = SchemaAwareArgumentBuilder(tool_schema)
   args = builder.build_args(data_mapping, context)
   
   # Contract test before call
   MCPContractTester.generate_test_report('toolName', tool_schema, args)
   ```

4. **Invocation**
   ```python
   # Call tool
   result = tool.invoke(input=args)
   ```

5. **Response Handling**
   ```python
   # Parse response
   parser = MCPResponseParser()
   parsed = parser.parse(result, expected_format=MCPResponseParser.FORMAT_ROVO)
   ```

## Common Issues Prevented

| Issue | Prevention Strategy |
|-------|-------------------|
| Type mismatch | `SchemaAwareArgumentBuilder` auto-converts types |
| Wrong parameter names | Flexible parameter name mapping |
| Missing required params | Builder validates required params |
| Invalid enum values | Builder validates enums against schema |
| Wrong response parsing | `MCPResponseParser` handles multiple formats |
| Schema not understood | `MCPSchemaValidator` provides clear analysis |

## Example Integration

See `examples/mcp_integration_example.py` for a complete working example.

## Checklist

Use `docs/mcp_integration_checklist.md` for step-by-step validation.

## Key Takeaways

1. **Always validate schema first** - Use `MCPSchemaValidator.print_schema_analysis()`
2. **Use argument builder** - Don't manually build arguments
3. **Test contracts** - Run `MCPContractTester` before tool calls
4. **Use response parser** - Don't manually parse responses
5. **Follow checklist** - Use the integration checklist for each new tool

## Questions?

- Check the example: `examples/mcp_integration_example.py`
- Review the checklist: `docs/mcp_integration_checklist.md`
- Run validation: `python scripts/validate_mcp_tool.py --help`

