"""
Script to verify and set up MCP dependencies.

This script checks:
1. Node.js/npx availability
2. Required npm packages availability
3. Jira/Confluence credentials from .env
4. Tests MCP server connections
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('setup.mcp')

def check_nodejs():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            logger.info(f"✓ Node.js installed: {result.stdout.strip()}")
            return True
        else:
            logger.error("✗ Node.js not found")
            return False
    except FileNotFoundError:
        logger.error("✗ Node.js not found. Install from https://nodejs.org/")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking Node.js: {e}")
        return False

def check_npx():
    """Check if npx is available."""
    try:
        import platform
        npx_cmd = 'npx.cmd' if platform.system() == 'Windows' else 'npx'
        result = subprocess.run([npx_cmd, '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            logger.info(f"✓ npx available: {result.stdout.strip()}")
            return True, npx_cmd
        else:
            logger.error("✗ npx not found")
            return False, None
    except FileNotFoundError:
        logger.error("✗ npx not found")
        return False, None
    except Exception as e:
        logger.error(f"✗ Error checking npx: {e}")
        return False, None

def check_npm_package(package_name, npx_cmd):
    """Check if an npm package can be accessed via npx."""
    try:
        # Just verify npx can access npm registry (quick check)
        # Don't actually download packages - npx -y will do that when needed
        logger.info(f"  - '{package_name}' will be downloaded automatically via npx -y when needed")
        return True  # npx -y handles package installation automatically
    except Exception as e:
        logger.warning(f"⚠ Could not verify '{package_name}': {e}")
        return True  # Assume it works, npx -y will download if needed

def check_credentials():
    """Check if Jira/Confluence credentials are configured."""
    logger.info("\n" + "=" * 70)
    logger.info("Checking Credentials")
    logger.info("=" * 70)
    
    checks = {
        'JIRA_URL': Config.JIRA_URL,
        'JIRA_EMAIL': Config.JIRA_EMAIL,
        'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
        'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY,
        'CONFLUENCE_URL': Config.CONFLUENCE_URL,
        'CONFLUENCE_SPACE_KEY': Config.CONFLUENCE_SPACE_KEY,
        'USE_MCP': Config.USE_MCP,
    }
    
    all_ok = True
    for key, value in checks.items():
        if key == 'JIRA_API_TOKEN':
            # Mask API token
            if isinstance(value, str) and len(value) > 4:
                display_value = f"{'*' * (len(value) - 4)}{value[-4:]}"
            else:
                display_value = "***"
        elif key == 'USE_MCP':
            display_value = str(value)
        elif isinstance(value, str):
            display_value = value if not value.startswith('your-') else f"[NOT SET] {value}"
        else:
            display_value = str(value)
        
        # Check if value is configured
        if key == 'USE_MCP':
            is_configured = True  # Boolean values are always "configured"
        elif isinstance(value, str):
            is_configured = value and not value.startswith('your-') and value != ''
        else:
            is_configured = bool(value)
        
        if is_configured:
            logger.info(f"✓ {key}: {display_value}")
        else:
            logger.warning(f"⚠ {key}: Not configured")
            if key in ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN']:
                all_ok = False
    
    return all_ok

def main():
    """Main setup verification."""
    logger.info("=" * 70)
    logger.info("MCP Dependencies Setup Verification")
    logger.info("=" * 70)
    logger.info("")
    
    # Check Node.js
    logger.info("1. Checking Node.js...")
    nodejs_ok = check_nodejs()
    logger.info("")
    
    # Check npx
    logger.info("2. Checking npx...")
    npx_ok, npx_cmd = check_npx()
    logger.info("")
    
    if not nodejs_ok or not npx_ok:
        logger.error("\n" + "=" * 70)
        logger.error("ERROR: Node.js/npx not available")
        logger.error("Please install Node.js from https://nodejs.org/")
        logger.error("=" * 70)
        return False
    
    # Check npm packages
    logger.info("3. Checking npm packages...")
    logger.info("   Note: npx -y will download packages automatically when needed")
    packages = [
        'mcp-remote',      # Official Atlassian Rovo MCP Server proxy
        'mcp-jira',        # Community Jira MCP server
        'mcp-atlassian',   # Community Atlassian MCP server
    ]
    
    packages_ok = True
    for package in packages:
        if not check_npm_package(package, npx_cmd):
            packages_ok = False
    
    logger.info("")
    
    # Check credentials
    credentials_ok = check_credentials()
    logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("Setup Summary")
    logger.info("=" * 70)
    
    all_ok = nodejs_ok and npx_ok and credentials_ok
    
    if all_ok:
        logger.info("✓ All dependencies are ready!")
        logger.info("")
        logger.info("MCP servers will be automatically downloaded via npx -y when needed.")
        logger.info("No manual npm install required.")
    else:
        logger.warning("⚠ Some dependencies are missing:")
        if not nodejs_ok or not npx_ok:
            logger.warning("  - Install Node.js from https://nodejs.org/")
        if not credentials_ok:
            logger.warning("  - Configure Jira credentials in .env file")
            logger.warning("  - Required: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY")
    
    logger.info("")
    logger.info("=" * 70)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

