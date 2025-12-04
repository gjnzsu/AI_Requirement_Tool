"""
Diagnostic script to check if the environment is set up correctly.
Run this before running evaluate_jira_maturity.py to identify issues.
"""

import sys
from pathlib import Path

print("=" * 80)
print("Jira Maturity Evaluator - Setup Diagnostic")
print("=" * 80)

# Check Python version
print(f"\n✓ Python version: {sys.version}")

# Check if required packages are installed
print("\nChecking required packages...")
required_packages = {
    'jira': 'jira',
    'openai': 'openai',
    'dotenv': 'python-dotenv',
    'requests': 'requests'
}

missing_packages = []
for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"  ✓ {package_name} is installed")
    except ImportError:
        print(f"  ✗ {package_name} is NOT installed")
        missing_packages.append(package_name)

if missing_packages:
    print(f"\n⚠ Missing packages: {', '.join(missing_packages)}")
    print("  Install them with: pip install -r requirements-jira-service.txt")
else:
    print("\n✓ All required packages are installed")

# Check configuration
print("\nChecking configuration...")
try:
    from config.config import Config
    
    config_status = {
        'JIRA_URL': Config.JIRA_URL,
        'JIRA_EMAIL': Config.JIRA_EMAIL,
        'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
        'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY,
        'OPENAI_API_KEY': Config.OPENAI_API_KEY
    }
    
    all_set = True
    for key, value in config_status.items():
        if value.startswith('your-') or value == '':
            print(f"  ✗ {key}: Not set (using default: {value})")
            all_set = False
        else:
            # Mask sensitive values
            if 'TOKEN' in key or 'KEY' in key:
                masked = value[:8] + '...' if len(value) > 8 else '***'
                print(f"  ✓ {key}: {masked}")
            else:
                print(f"  ✓ {key}: {value}")
    
    if all_set:
        print("\n✓ All configuration values are set")
        if Config.validate():
            print("✓ Configuration validation passed")
        else:
            print("⚠ Configuration validation failed")
    else:
        print("\n⚠ Some configuration values are not set")
        print("  Set them as environment variables or create a .env file")
        
except Exception as e:
    print(f"  ✗ Error loading config: {e}")
    import traceback
    traceback.print_exc()

# Check if .env file exists
print("\nChecking for .env file...")
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    print("  ✓ .env file exists")
else:
    print("  ⚠ .env file not found (optional - can use environment variables instead)")

# Check project structure
print("\nChecking project structure...")
project_root = Path(__file__).parent
required_files = [
    'src/services/jira_maturity_evaluator.py',
    'config/config.py',
    'evaluate_jira_maturity.py'
]

all_files_exist = True
for file_path in required_files:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"  ✓ {file_path}")
    else:
        print(f"  ✗ {file_path} - MISSING")
        all_files_exist = False

if all_files_exist:
    print("\n✓ All required files are present")
else:
    print("\n⚠ Some required files are missing")

# Test imports
print("\nTesting imports...")
try:
    sys.path.insert(0, str(project_root))
    from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
    print("  ✓ JiraMaturityEvaluator imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import JiraMaturityEvaluator: {e}")
    import traceback
    traceback.print_exc()

try:
    from config.config import Config
    print("  ✓ Config imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import Config: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Diagnostic complete!")
print("=" * 80)

if missing_packages:
    print("\n⚠ ACTION REQUIRED: Install missing packages")
    print("   Run: pip install -r requirements-jira-service.txt")
elif not all_set:
    print("\n⚠ ACTION REQUIRED: Set configuration values")
    print("   See SETUP_ENV.md for instructions")
else:
    print("\n✓ Setup looks good! You should be able to run:")
    print("   python evaluate_jira_maturity.py")

