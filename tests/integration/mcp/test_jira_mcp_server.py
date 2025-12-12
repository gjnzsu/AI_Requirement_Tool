"""
Comprehensive test script for Jira MCP Server connections.

This script tests all available MCP server options and provides detailed diagnostics.
"""

import sys
import asyncio
import pytest
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger
logger = get_logger('test.jira_mcp_server')

from src.mcp.mcp_client import (
    MCPClient, 
    create_rovo_mcp_client, 
    create_jira_mcp_client,
    create_confluence_mcp_client
)
from config.config import Config


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    logger.info(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    logger.info(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    logger.warning(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    logger.error(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    logger.info(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


@pytest.mark.asyncio
async def test_rovo_mcp_server() -> Dict[str, Any]:
    """Test Atlassian Rovo MCP Server (Official)."""
    print_header("Test 1: Atlassian Rovo MCP Server (Official)")
    
    result = {
        'name': 'Atlassian Rovo MCP Server',
        'success': False,
        'error': None,
        'tools': [],
        'details': {}
    }
    
    try:
        print_info("Creating Rovo MCP client...")
        client = create_rovo_mcp_client()
        
        if not client:
            result['error'] = "Client creation failed - mcp-remote may not be installed"
            print_error("Failed to create Rovo MCP client")
            print_info("Install with: npm install -g mcp-remote")
            return result
        
        print_success("Rovo MCP client created")
        print_info(f"Command: {' '.join(client.command)}")
        
        print_info("Attempting to connect...")
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
            
            tools = client.get_tools()
            result['tools'] = list(tools.keys())
            result['success'] = True
            result['details'] = {
                'command': ' '.join(client.command),
                'tools_count': len(tools)
            }
            
            print_success(f"Connected successfully!")
            print_info(f"Available tools: {len(tools)}")
            if tools:
                for tool_name in tools.keys():
                    logger.info(f"  - {tool_name}")
            else:
                print_warning("No tools discovered")
                
        except asyncio.TimeoutError:
            result['error'] = "Connection timeout (15 seconds)"
            print_error("Connection timeout")
        except Exception as e:
            result['error'] = str(e)
            print_error(f"Connection failed: {e}")
            print_info("This may require OAuth 2.1 authentication in a browser")
            traceback.print_exc()
            
    except Exception as e:
        result['error'] = str(e)
        print_error(f"Test failed: {e}")
        traceback.print_exc()
    
    return result


@pytest.mark.asyncio
@pytest.mark.skip(reason="Community mcp-jira package not used in production - app uses custom Python-based Jira MCP server only")
async def test_community_jira_servers() -> Dict[str, Any]:
    """Test community Jira MCP server packages.
    
    DISABLED: This test is skipped because the application does not use community mcp-jira package.
    The app only uses custom Python-based Jira MCP server (jira_mcp_server.py).
    """
    print_header("Test 2: Community Jira MCP Servers")
    
    results = {
        'mcp-jira': {'success': False, 'error': None, 'tools': []},
        'mcp-atlassian': {'success': False, 'error': None, 'tools': []}
    }
    
    import platform
    import shutil
    is_windows = platform.system() == 'Windows'
    npx_cmd = 'npx.cmd' if is_windows else 'npx'
    
    # Check if credentials are configured
    has_credentials = (
        Config.JIRA_URL and not Config.JIRA_URL.startswith('https://yourcompany') and
        Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
        Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'
    )
    
    if not has_credentials:
        print_warning("Jira credentials not configured")
        print_info("Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env file")
        return results
    
    # Test mcp-jira
    print_info("\nTesting mcp-jira...")
    try:
        command = [npx_cmd, '-y', 'mcp-jira']
        env = {
            'JIRA_URL': Config.JIRA_URL,
            'JIRA_EMAIL': Config.JIRA_EMAIL,
            'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
            'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY
        }
        
        client = MCPClient('mcp-jira', command, env)
        print_info(f"Command: {' '.join(command)}")
        
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
            tools = client.get_tools()
            results['mcp-jira'] = {
                'success': True,
                'tools': list(tools.keys()),
                'error': None
            }
            print_success(f"mcp-jira connected! Tools: {len(tools)}")
            for tool_name in tools.keys():
                logger.info(f"  - {tool_name}")
        except Exception as e:
            results['mcp-jira']['error'] = str(e)
            print_error(f"mcp-jira connection failed: {e}")
            if "not found" in str(e).lower():
                print_info("Install with: npm install -g mcp-jira")
    except Exception as e:
        results['mcp-jira']['error'] = str(e)
        print_error(f"mcp-jira test failed: {e}")
    
    # Test mcp-atlassian
    print_info("\nTesting mcp-atlassian...")
    try:
        command = [npx_cmd, '-y', 'mcp-atlassian']
        env = {
            'JIRA_URL': Config.JIRA_URL,
            'JIRA_EMAIL': Config.JIRA_EMAIL,
            'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
            'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY,
            'ATLASSIAN_URL': Config.JIRA_URL,
        }
        
        client = MCPClient('mcp-atlassian', command, env)
        print_info(f"Command: {' '.join(command)}")
        
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
            tools = client.get_tools()
            results['mcp-atlassian'] = {
                'success': True,
                'tools': list(tools.keys()),
                'error': None
            }
            print_success(f"mcp-atlassian connected! Tools: {len(tools)}")
            for tool_name in tools.keys():
                logger.info(f"  - {tool_name}")
        except Exception as e:
            results['mcp-atlassian']['error'] = str(e)
            print_error(f"mcp-atlassian connection failed: {e}")
            if "not found" in str(e).lower():
                print_info("Install with: npm install -g mcp-atlassian")
    except Exception as e:
        results['mcp-atlassian']['error'] = str(e)
        print_error(f"mcp-atlassian test failed: {e}")
    
    return results


@pytest.mark.asyncio
async def test_mcp_integration() -> Dict[str, Any]:
    """Test the full MCP integration."""
    print_header("Test 3: Full MCP Integration")
    
    result = {
        'success': False,
        'error': None,
        'tools': [],
        'details': {}
    }
    
    try:
        from src.mcp.mcp_integration import MCPIntegration
        
        print_info("Initializing MCP Integration...")
        integration = MCPIntegration(use_mcp=True)
        
        print_info("Connecting to MCP servers...")
        await asyncio.wait_for(integration.initialize(), timeout=20.0)
        
        if integration._initialized:
            tools = integration.get_tools()
            result['success'] = True
            result['tools'] = [tool.name for tool in tools]
            result['details'] = {
                'tools_count': len(tools),
                'initialized': True
            }
            
            print_success("MCP Integration initialized successfully!")
            print_info(f"Total tools available: {len(tools)}")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description[:60]}...")
        else:
            result['error'] = "Integration not initialized"
            print_warning("MCP Integration not initialized")
            print_info("Falling back to custom tools")
            
    except asyncio.TimeoutError:
        result['error'] = "Integration timeout"
        print_error("Integration timeout")
    except Exception as e:
        result['error'] = str(e)
        print_error(f"Integration failed: {e}")
        traceback.print_exc()
    
    return result


@pytest.mark.asyncio
async def test_custom_tools() -> Dict[str, Any]:
    """Test custom tools fallback."""
    print_header("Test 4: Custom Tools (Fallback)")
    
    result = {
        'success': False,
        'error': None,
        'tools': []
    }
    
    try:
        from src.tools.jira_tool import JiraTool
        
        print_info("Testing custom JiraTool...")
        tool = JiraTool()
        result['success'] = True
        result['tools'] = ['jira_tool']
        
        print_success("Custom JiraTool is available")
        print_info("This will be used if MCP servers are unavailable")
        
    except Exception as e:
        result['error'] = str(e)
        print_error(f"Custom tool test failed: {e}")
        print_warning("Check Jira credentials in .env file")
    
    return result


def print_summary(all_results: Dict[str, Any]):
    """Print test summary."""
    print_header("Test Summary")
    
    # Rovo test
    rovo = all_results.get('rovo', {})
    if rovo.get('success'):
        print_success(f"Atlassian Rovo MCP Server: ✓ Working ({len(rovo.get('tools', []))} tools)")
    else:
        print_warning(f"Atlassian Rovo MCP Server: ✗ Failed - {rovo.get('error', 'Unknown error')}")
    
    # Community servers
    community = all_results.get('community', {})
    for name, result in community.items():
        if result.get('success'):
            print_success(f"{name}: ✓ Working ({len(result.get('tools', []))} tools)")
        else:
            print_warning(f"{name}: ✗ Failed - {result.get('error', 'Unknown error')}")
    
    # Integration test
    integration = all_results.get('integration', {})
    if integration.get('success'):
        print_success(f"MCP Integration: ✓ Working ({len(integration.get('tools', []))} tools)")
    else:
        print_warning(f"MCP Integration: ✗ Failed - {integration.get('error', 'Unknown error')}")
    
    # Custom tools
    custom = all_results.get('custom', {})
    if custom.get('success'):
        print_success(f"Custom Tools: ✓ Available (fallback option)")
    else:
        print_error(f"Custom Tools: ✗ Failed - {custom.get('error', 'Unknown error')}")
    
    logger.info("\n" + "=" * 70)
    logger.info(f"{Colors.BOLD}Recommendations:{Colors.RESET}")
    logger.info("=" * 70)
    
    # Provide recommendations
    if rovo.get('success'):
        print_info("✓ Use Atlassian Rovo MCP Server (Official) - Best option!")
    elif any(r.get('success') for r in community.values()):
        working = [name for name, r in community.items() if r.get('success')]
        print_info(f"✓ Use community package: {working[0]}")
    elif custom.get('success'):
        print_info("✓ Use custom tools - They work perfectly as fallback")
    else:
        print_warning("⚠ No MCP servers working. Check:")
        logger.info("  1. Node.js and npm are installed")
        logger.info("  2. MCP server packages are installed (npm install -g mcp-remote)")
        logger.info("  3. Jira credentials are configured in .env file")
    
    logger.info("")


async def main():
    """Run all tests."""
    print_header("Jira MCP Server Diagnostic Test")
    
    print_info("This script will test all available MCP server options")
    print_info("and provide detailed diagnostics for connection issues.\n")
    
    all_results = {}
    
    # Test 1: Rovo MCP Server
    all_results['rovo'] = await test_rovo_mcp_server()
    
    # Test 2: Community servers
    # DISABLED: Community Jira MCP servers not used in production
    # all_results['community'] = await test_community_jira_servers()
    all_results['community'] = {'skipped': True, 'reason': 'Community mcp-jira not used - app uses custom Python-based server'}
    
    # Test 3: Full integration
    all_results['integration'] = await test_mcp_integration()
    
    # Test 4: Custom tools
    all_results['custom'] = await test_custom_tools()
    
    # Print summary
    print_summary(all_results)
    
    print_header("Test Complete")
    print_info("The chatbot will automatically use the best available option:")
    logger.info("  1. Atlassian Rovo MCP Server (if available)")
    logger.info("  2. Community MCP packages (if available)")
    logger.info("  3. Custom tools (always available)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        traceback.print_exc()

