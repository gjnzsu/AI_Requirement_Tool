"""
Schema Validation Utilities for MCP Tool Integration.

Provides utilities to validate and analyze MCP tool schemas before integration,
helping catch issues early in the development process.
"""

from typing import Dict, List, Any, Optional, Tuple


class MCPSchemaValidator:
    """Validates and analyzes MCP tool schemas."""
    
    @staticmethod
    def validate_schema_structure(tool_schema: Dict) -> Tuple[bool, List[str]]:
        """
        Validate that tool schema has required structure.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if not tool_schema:
            issues.append("Tool schema is None or empty")
            return False, issues
        
        if 'inputSchema' not in tool_schema:
            issues.append("Missing 'inputSchema' in tool schema")
            return False, issues
        
        input_schema = tool_schema['inputSchema']
        if 'properties' not in input_schema:
            issues.append("Missing 'properties' in inputSchema")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def analyze_schema(tool_name: str, tool_schema: Dict) -> Dict[str, Any]:
        """
        Analyze tool schema and return structured information.
        
        Returns:
            Dictionary with schema analysis results
        """
        analysis = {
            'tool_name': tool_name,
            'has_schema': False,
            'required_params': [],
            'optional_params': [],
            'parameter_details': {},
            'enum_parameters': {},
            'issues': []
        }
        
        if not tool_schema or 'inputSchema' not in tool_schema:
            analysis['issues'].append("No schema available")
            return analysis
        
        analysis['has_schema'] = True
        input_schema = tool_schema['inputSchema']
        properties = input_schema.get('properties', {})
        required = input_schema.get('required', [])
        
        analysis['required_params'] = required
        
        for param_name, param_def in properties.items():
            is_required = param_name in required
            param_type = param_def.get('type', 'unknown')
            enum_values = param_def.get('enum', [])
            description = param_def.get('description', '')
            
            param_info = {
                'type': param_type,
                'required': is_required,
                'enum_values': enum_values,
                'description': description
            }
            
            analysis['parameter_details'][param_name] = param_info
            
            if enum_values:
                analysis['enum_parameters'][param_name] = enum_values
            
            if not is_required:
                analysis['optional_params'].append(param_name)
        
        return analysis
    
    @staticmethod
    def print_schema_analysis(tool_name: str, tool_schema: Dict):
        """Print human-readable schema analysis."""
        analysis = MCPSchemaValidator.analyze_schema(tool_name, tool_schema)
        
        print(f"\n{'='*60}")
        print(f"Schema Analysis: {tool_name}")
        print(f"{'='*60}")
        
        if not analysis['has_schema']:
            print("⚠️  No schema available")
            return
        
        print(f"\n📋 Parameters:")
        print(f"   Required ({len(analysis['required_params'])}): {', '.join(analysis['required_params'])}")
        print(f"   Optional ({len(analysis['optional_params'])}): {', '.join(analysis['optional_params'][:5])}")
        
        print(f"\n📝 Parameter Details:")
        for param_name, param_info in analysis['parameter_details'].items():
            req_marker = "✓ REQUIRED" if param_info['required'] else "  optional"
            print(f"   {req_marker} {param_name}: {param_info['type']}")
            
            if param_info['enum_values']:
                print(f"      Enum values: {param_info['enum_values']}")
            
            if param_info['description']:
                desc = param_info['description'][:60]
                print(f"      {desc}...")
        
        if analysis['enum_parameters']:
            print(f"\n🔢 Enum Parameters:")
            for param, values in analysis['enum_parameters'].items():
                print(f"   - {param}: {values}")
        
        if analysis['issues']:
            print(f"\n⚠️  Issues:")
            for issue in analysis['issues']:
                print(f"   - {issue}")


class MCPContractTester:
    """Tests contracts between code and MCP tool schemas."""
    
    @staticmethod
    def test_parameter_types(tool_schema: Dict, sample_args: Dict) -> List[Dict]:
        """
        Test that sample arguments match expected types from schema.
        
        Returns:
            List of type violations
        """
        violations = []
        
        if not tool_schema or 'inputSchema' not in tool_schema:
            return violations
        
        properties = tool_schema['inputSchema'].get('properties', {})
        
        for param_name, value in sample_args.items():
            if param_name not in properties:
                continue  # Unknown parameter, not a type violation
            
            param_def = properties[param_name]
            expected_type = param_def.get('type', 'string')
            actual_type = type(value).__name__
            
            # Type mapping JSON Schema -> Python
            type_map = {
                'string': str,
                'integer': int,
                'number': float,
                'boolean': bool
            }
            
            expected_python_type = type_map.get(expected_type, str)
            
            if not isinstance(value, expected_python_type):
                violations.append({
                    'param': param_name,
                    'expected_schema_type': expected_type,
                    'expected_python_type': expected_python_type.__name__,
                    'actual_type': actual_type,
                    'actual_value': value
                })
        
        return violations
    
    @staticmethod
    def test_required_parameters(tool_schema: Dict, args: Dict) -> List[str]:
        """Test that all required parameters are present."""
        if not tool_schema or 'inputSchema' not in tool_schema:
            return []
        
        required = tool_schema['inputSchema'].get('required', [])
        missing = [p for p in required if p not in args]
        return missing
    
    @staticmethod
    def test_enum_values(tool_schema: Dict, args: Dict) -> List[Dict]:
        """Test that enum values are valid."""
        violations = []
        
        if not tool_schema or 'inputSchema' not in tool_schema:
            return violations
        
        properties = tool_schema['inputSchema'].get('properties', {})
        
        for param_name, value in args.items():
            if param_name not in properties:
                continue
            
            param_def = properties[param_name]
            enum_values = param_def.get('enum', [])
            
            if enum_values and value not in enum_values:
                violations.append({
                    'param': param_name,
                    'value': value,
                    'allowed_values': enum_values
                })
        
        return violations
    
    @staticmethod
    def generate_test_report(tool_name: str, tool_schema: Dict, sample_args: Dict) -> bool:
        """Generate comprehensive contract test report."""
        print(f"\n{'='*60}")
        print(f"Contract Test Report: {tool_name}")
        print(f"{'='*60}")
        
        all_passed = True
        
        # Test required params
        missing = MCPContractTester.test_required_parameters(tool_schema, sample_args)
        if missing:
            print(f"❌ Missing required parameters: {missing}")
            all_passed = False
        else:
            print(f"✅ All required parameters present")
        
        # Test types
        type_violations = MCPContractTester.test_parameter_types(tool_schema, sample_args)
        if type_violations:
            print(f"❌ Type violations:")
            for v in type_violations:
                print(f"   - {v['param']}: expected {v['expected_schema_type']} "
                      f"({v['expected_python_type']}), got {v['actual_type']} "
                      f"(value: {v['actual_value']})")
            all_passed = False
        else:
            print(f"✅ All parameter types match schema")
        
        # Test enums
        enum_violations = MCPContractTester.test_enum_values(tool_schema, sample_args)
        if enum_violations:
            print(f"❌ Enum violations:")
            for v in enum_violations:
                print(f"   - {v['param']}: value '{v['value']}' not in {v['allowed_values']}")
            all_passed = False
        else:
            print(f"✅ All enum values valid")
        
        if all_passed:
            print(f"\n✅ All contract tests passed!")
        else:
            print(f"\n⚠️  Contract violations detected - please fix before integration")
        
        return all_passed

