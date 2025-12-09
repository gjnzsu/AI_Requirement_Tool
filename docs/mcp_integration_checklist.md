# MCP Service Integration Checklist

Use this checklist when integrating a new MCP service to avoid common pitfalls.

## Phase 1: Discovery & Analysis

- [ ] **Tool Schema Retrieved**
  - [ ] Tool schema is accessible via `tool._tool_schema` or `tool.args_schema`
  - [ ] Run `MCPSchemaValidator.print_schema_analysis(tool_name, tool_schema)`

- [ ] **Required Parameters Identified**
  - [ ] List all required parameters from schema
  - [ ] Document parameter types and constraints
  - [ ] Note any enum values

- [ ] **Parameter Types Documented**
  - [ ] Check each parameter type (string, integer, number, boolean)
  - [ ] Note any special type requirements (e.g., string representation of numeric ID)
  - [ ] Document any type conversions needed

- [ ] **Enum Values Documented**
  - [ ] List all enum parameters
  - [ ] Document valid enum values
  - [ ] Note default values if any

- [ ] **Response Format Documented**
  - [ ] Identify response format (Rovo, Custom, Generic)
  - [ ] Document success indicators (id field, success flag, etc.)
  - [ ] Note key fields returned (id, title, link, etc.)

- [ ] **Authentication Requirements Identified**
  - [ ] Check if tool requires `cloudId`
  - [ ] Check if tool requires other auth parameters
  - [ ] Document how to retrieve these parameters

## Phase 2: Schema Validation

- [ ] **Schema Contract Test Passes**
  - [ ] Run `MCPContractTester.generate_test_report()`
  - [ ] All type checks pass
  - [ ] All enum validations pass

- [ ] **Type Conversions Validated**
  - [ ] Test conversion from internal format to tool format
  - [ ] Verify string/int/number conversions
  - [ ] Test enum value matching

- [ ] **Required Parameters Verified**
  - [ ] All required parameters can be provided
  - [ ] Dependencies resolved (e.g., cloudId, spaceId)

## Phase 3: Implementation

- [ ] **Tool Selection Logic Implemented**
  - [ ] Tool can be identified correctly
  - [ ] Safety checks prevent wrong tool selection
  - [ ] Fallback mechanism in place

- [ ] **Argument Builder Configured**
  - [ ] Use `SchemaAwareArgumentBuilder` for argument construction
  - [ ] Parameter mappings configured
  - [ ] Type conversions handled automatically

- [ ] **Type Conversions Implemented**
  - [ ] All type conversions handled by argument builder
  - [ ] Edge cases tested (string numbers, etc.)

- [ ] **Response Parsing Implemented**
  - [ ] Use `MCPResponseParser` for response parsing
  - [ ] Correct format specified (Rovo/Custom/Generic)
  - [ ] Success detection logic verified

- [ ] **Error Handling Implemented**
  - [ ] Error responses parsed correctly
  - [ ] Helpful error messages provided
  - [ ] Fallback mechanisms work

## Phase 4: Testing

- [ ] **Unit Tests for Argument Building**
  - [ ] Test argument builder with sample data
  - [ ] Test type conversions
  - [ ] Test parameter name variations

- [ ] **Unit Tests for Type Conversions**
  - [ ] Test each type conversion
  - [ ] Test edge cases
  - [ ] Test enum validation

- [ ] **Contract Tests for Tool Invocation**
  - [ ] Test parameter types match schema
  - [ ] Test required parameters
  - [ ] Test enum values

- [ ] **Integration Test for Full Flow**
  - [ ] Test end-to-end flow
  - [ ] Verify success scenarios
  - [ ] Test error scenarios

- [ ] **Error Scenario Tests**
  - [ ] Test missing required parameters
  - [ ] Test invalid enum values
  - [ ] Test type mismatches
  - [ ] Test network errors

## Phase 5: Validation

- [ ] **Success Scenarios Tested**
  - [ ] Tool invocation succeeds
  - [ ] Response parsed correctly
  - [ ] Result stored correctly

- [ ] **Error Scenarios Tested**
  - [ ] Errors handled gracefully
  - [ ] Fallback works
  - [ ] Error messages helpful

- [ ] **Edge Cases Handled**
  - [ ] Missing optional parameters
  - [ ] Null/empty values
  - [ ] Large responses
  - [ ] Timeout scenarios

- [ ] **Logging Adequate for Debugging**
  - [ ] Schema analysis logged
  - [ ] Arguments logged before call
  - [ ] Response logged after call
  - [ ] Errors logged with context

## Quick Validation Script

Run before integration:
```bash
python scripts/validate_mcp_tool.py --tool <tool_name> --schema-file <schema.json>
```

## Common Pitfalls to Avoid

1. **Type Mismatches**: Always check schema type and convert accordingly
2. **Enum Values**: Verify enum values from schema, don't assume
3. **Required Parameters**: Ensure all required params are provided
4. **Response Format**: Identify format (Rovo vs Custom) and parse accordingly
5. **ID Conversions**: Check if IDs need to be string or number
6. **Authentication**: Verify cloudId/spaceId retrieval works
7. **Error Handling**: Parse error responses correctly

## Example Integration Template

```python
from src.mcp import SchemaAwareArgumentBuilder, MCPResponseParser, MCPSchemaValidator

# 1. Get tool and schema
tool = mcp_integration.get_tool('toolName')
tool_schema = tool._tool_schema

# 2. Analyze schema
MCPSchemaValidator.print_schema_analysis('toolName', tool_schema)

# 3. Build arguments
builder = SchemaAwareArgumentBuilder(tool_schema)
args = builder.build_args(
    data_mapping={
        'title': 'My Title',
        'content': 'My Content',
    },
    context={
        'cloudId': cloud_id,
        'spaceId': space_id,
    }
)

# 4. Call tool
result = tool.invoke(input=args)

# 5. Parse response
parser = MCPResponseParser()
parsed = parser.parse(result, expected_format=MCPResponseParser.FORMAT_ROVO)
```

