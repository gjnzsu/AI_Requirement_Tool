"""
Schema-Aware Argument Builder for MCP Tools.

Automatically builds arguments from tool schemas with proper type conversion
and validation, preventing type mismatch and parameter errors.
"""

from typing import Dict, List, Any, Optional
from config.config import Config


class SchemaAwareArgumentBuilder:
    """Automatically builds arguments from tool schema."""
    
    def __init__(self, tool_schema: Dict):
        """
        Initialize with tool schema.
        
        Args:
            tool_schema: Tool schema dictionary from MCP
        """
        self.schema = tool_schema
        self.input_schema = tool_schema.get('inputSchema', {}) if tool_schema else {}
        self.properties = self.input_schema.get('properties', {})
        self.required = self.input_schema.get('required', [])
    
    def build_args(self, data_mapping: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build arguments from data mapping, automatically handling:
        - Type conversions
        - Enum validation
        - Required parameter checking
        - Parameter name variations
        
        Args:
            data_mapping: Dictionary with data to map to parameters
            context: Additional context (e.g., cloudId, spaceId)
            
        Returns:
            Dictionary with properly typed and validated arguments
        """
        context = context or {}
        args = {}
        
        # Build parameter mapping from schema
        param_mapping = self._build_parameter_mapping()
        
        # Map data to schema parameters
        for param_name, param_def in self.properties.items():
            # Try to find matching data
            value = self._find_value_for_param(param_name, data_mapping, param_mapping, context)
            
            if value is None:
                # Check if required
                if param_name in self.required:
                    # Try to get from context or use default
                    value = context.get(param_name) or self._get_default_value(param_def)
                    if value is None:
                        raise ValueError(
                            f"Required parameter '{param_name}' not provided. "
                            f"Required parameters: {self.required}"
                        )
                else:
                    # Optional parameter, skip
                    continue
            
            # Convert type based on schema
            converted_value = self._convert_type(value, param_def, param_name)
            
            # Validate enum if applicable
            self._validate_enum(converted_value, param_def, param_name)
            
            args[param_name] = converted_value
        
        return args
    
    def _convert_type(self, value: Any, param_def: Dict, param_name: str) -> Any:
        """
        Convert value to match schema type.
        
        Args:
            value: Value to convert
            param_def: Parameter definition from schema
            param_name: Parameter name (for error messages)
            
        Returns:
            Converted value matching schema type
        """
        if value is None:
            return None
        
        expected_type = param_def.get('type', 'string')
        
        try:
            if expected_type == 'string':
                return str(value)
            elif expected_type == 'integer':
                # Convert to int, handling string numbers
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                return int(value) if value is not None else None
            elif expected_type == 'number':
                # Convert to float, handling string numbers
                if isinstance(value, str):
                    return float(value)
                return float(value) if value is not None else None
            elif expected_type == 'boolean':
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value) if value is not None else None
            else:
                # Unknown type, return as-is
                return value
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Cannot convert '{param_name}' value '{value}' to type '{expected_type}': {e}"
            )
    
    def _validate_enum(self, value: Any, param_def: Dict, param_name: str):
        """
        Validate enum value if schema specifies enum.
        
        Args:
            value: Value to validate
            param_def: Parameter definition from schema
            param_name: Parameter name (for error messages)
            
        Raises:
            ValueError if enum value is invalid
        """
        enum_values = param_def.get('enum', [])
        if enum_values and value not in enum_values:
            raise ValueError(
                f"Invalid value for '{param_name}': '{value}'. "
                f"Allowed values: {enum_values}"
            )
    
    def _find_value_for_param(
        self, 
        param_name: str, 
        data: Dict, 
        mapping: Dict,
        context: Dict
    ) -> Optional[Any]:
        """
        Find value for parameter using flexible matching.
        
        Args:
            param_name: Target parameter name
            data: Data mapping dictionary
            mapping: Parameter name mapping
            context: Additional context
            
        Returns:
            Found value or None
        """
        # Direct match
        if param_name in data:
            return data[param_name]
        
        # Check context
        if param_name in context:
            return context[param_name]
        
        # Check mapping for alternatives
        if param_name in mapping:
            for alt_name in mapping[param_name]:
                if alt_name in data:
                    return data[alt_name]
                if alt_name in context:
                    return context[alt_name]
        
        # Try case-insensitive match
        param_lower = param_name.lower()
        for key in data.keys():
            if key.lower() == param_lower:
                return data[key]
        
        return None
    
    def _build_parameter_mapping(self) -> Dict[str, List[str]]:
        """
        Build flexible parameter name mapping.
        
        Returns:
            Dictionary mapping parameter names to alternative names
        """
        mapping = {}
        
        # Common parameter name patterns
        common_mappings = {
            'title': ['name', 'pageTitle', 'page_title', 'summary'],
            'content': ['body', 'html', 'text', 'description'],
            'space': ['spaceKey', 'space_key', 'spaceId', 'space_id'],
            'spaceId': ['space_id', 'spaceKey', 'space_key'],
            'cloudId': ['cloud_id'],
            'contentFormat': ['content_format', 'format'],
        }
        
        for param_name in self.properties.keys():
            alternatives = [param_name]
            
            # Add from common mappings
            param_lower = param_name.lower()
            for pattern, alts in common_mappings.items():
                if pattern.lower() == param_lower or pattern.lower() in param_lower:
                    alternatives.extend(alts)
            
            # Add common variations
            if 'id' in param_lower:
                alternatives.extend([
                    param_name.replace('Id', '_id'),
                    param_name.replace('id', 'ID'),
                    param_name.replace('Id', 'Key'),  # Sometimes ID/Key are interchangeable
                ])
            if 'key' in param_lower:
                alternatives.extend([
                    param_name.replace('Key', '_key'),
                    param_name.replace('key', 'ID'),  # Sometimes Key/ID are interchangeable
                ])
            
            mapping[param_name] = list(set(alternatives))  # Remove duplicates
        
        return mapping
    
    def _get_default_value(self, param_def: Dict) -> Optional[Any]:
        """Get default value from parameter definition."""
        if 'default' in param_def:
            return param_def['default']
        return None
    
    def get_required_params(self) -> List[str]:
        """Get list of required parameter names."""
        return self.required.copy()
    
    def get_optional_params(self) -> List[str]:
        """Get list of optional parameter names."""
        return [p for p in self.properties.keys() if p not in self.required]
    
    def has_param(self, param_name: str) -> bool:
        """Check if parameter exists in schema."""
        return param_name in self.properties
    
    def get_param_type(self, param_name: str) -> Optional[str]:
        """Get parameter type from schema."""
        param_def = self.properties.get(param_name, {})
        return param_def.get('type', None)
    
    def get_enum_values(self, param_name: str) -> Optional[List[Any]]:
        """Get enum values for parameter if applicable."""
        param_def = self.properties.get(param_name, {})
        return param_def.get('enum', None)

