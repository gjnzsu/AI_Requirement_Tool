# Mocking Guide for Tests

## Common Pitfalls and Solutions

### Problem: Patching Imported Objects

When modules import objects (like `Config`), they hold references to those objects. Patching the import path doesn't always affect already-imported references.

#### ❌ Wrong Approach 1: Patching the source module
```python
with patch('config.config.Config') as mock_config:
    mock_config.JWT_SECRET_KEY = 'test'
```
**Problem**: Modules that already imported `Config` may not see the patch.

#### ❌ Wrong Approach 2: Patching where it's imported
```python
with patch('src.auth.user_service.Config') as mock_config:
    mock_config.JWT_SECRET_KEY = 'test'
```
**Problem**: Unreliable - depends on import order and may not affect all modules.

#### ✅ Correct Approach: Using `patch.object` on the actual object
```python
from config.config import Config

with patch.object(Config, 'JWT_SECRET_KEY', 'test'):
    # All modules that imported Config will see this value
    pass
```
**Why it works**: Patches the actual class object that all modules reference.

### Best Practices

1. **Import the object first, then patch it**
   ```python
   from config.config import Config
   with patch.object(Config, 'ATTR', value):
       # Use the patched value
   ```

2. **Restore original values in finally block**
   ```python
   original_value = Config.ATTR
   try:
       with patch.object(Config, 'ATTR', new_value):
           # Test code
   finally:
       Config.ATTR = original_value
   ```

3. **Use `patch.object` for class attributes**
   - More reliable than patching import paths
   - Works with already-imported modules
   - No MagicMock overhead

4. **Verify the patch is applied**
   ```python
   with patch.object(Config, 'ATTR', 'test'):
       assert Config.ATTR == 'test'  # Verify patch works
   ```

### When to Use Each Method

- **`patch.object(obj, 'attr', value)`**: When patching attributes on an already-imported object
- **`patch('module.path')`**: When you need to replace an entire object before it's imported
- **`patch.object(obj, 'method')`**: When patching methods on an object

### Example: Fixing Config Mocking

```python
def test_something():
    from config.config import Config
    
    # Save original
    original = Config.JWT_SECRET_KEY
    
    try:
        # Patch the actual object
        with patch.object(Config, 'JWT_SECRET_KEY', 'test-value'):
            # All modules using Config will see 'test-value'
            service = SomeService()
            assert service.uses_config_correctly()
    finally:
        # Restore original
        Config.JWT_SECRET_KEY = original
```

