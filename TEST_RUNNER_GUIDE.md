# Test Suite Runner Guide

This guide explains how to run the full test suite for the Generative AI Chatbot project.

## Quick Start

### Run All Tests
```bash
# From the project root directory
cd generative-ai-chatbot

# Run all tests
python -m pytest tests/ -v

# Or using the test runner script
python run_tests.py
```

## Test Organization

The test suite is organized into the following categories:

- **Unit Tests** (`tests/unit/`) - Isolated component tests
- **Integration Tests** (`tests/integration/`) - Component interaction tests
  - API Tests (`tests/integration/api/`) - REST API endpoint tests
  - Agent Tests (`tests/integration/agent/`) - Agent framework tests
  - LLM Tests (`tests/integration/llm/`) - LLM provider tests
  - MCP Tests (`tests/integration/mcp/`) - MCP integration tests
  - Memory Tests (`tests/integration/memory/`) - Memory system tests
  - RAG Tests (`tests/integration/rag/`) - RAG service tests
- **E2E Tests** (`tests/e2e/`) - End-to-end workflow tests

## Running Tests

### Method 1: Using pytest Directly

#### Run All Tests
```bash
python -m pytest tests/ -v
```

#### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# API tests only
python -m pytest tests/integration/api/ -v

# Authentication tests only
python -m pytest tests/integration/api/test_auth_api.py -v

# Specific test file
python -m pytest tests/integration/api/test_auth_api.py::TestAuthAPI::test_login_success -v
```

#### Run Tests by Marker
```bash
# Run all API tests
python -m pytest -m api -v

# Run all MCP tests
python -m pytest -m mcp -v

# Run all RAG tests
python -m pytest -m rag -v

# Run all agent tests
python -m pytest -m agent -v

# Run all LLM tests
python -m pytest -m llm -v

# Run all memory tests
python -m pytest -m memory -v

# Run all unit tests
python -m pytest -m unit -v
```

#### Run Tests with Coverage
```bash
# Install coverage first: pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Method 2: Using Test Runner Scripts

#### Run All Tests
```bash
python run_tests.py
```

#### Run Specific Categories
```bash
# Unit tests
python run_tests.py --unit

# Integration tests
python run_tests.py --integration

# MCP tests
python run_tests.py --mcp

# RAG tests
python run_tests.py --rag

# Agent tests
python run_tests.py --agent

# LLM tests
python run_tests.py --llm

# Memory tests
python run_tests.py --memory

# Show help
python run_tests.py --help
```

### Method 3: Using Comprehensive Test Runner

```bash
# Run comprehensive test suite with detailed reporting
python run_all_tests.py
```

This script runs tests systematically by category and provides a detailed summary report.

## Test Configuration

The test configuration is defined in `pytest.ini`:

- **Default timeout**: 30 seconds per test
- **Output**: Verbose mode with short traceback
- **Markers**: Available for test categorization
- **Test discovery**: Automatically finds `test_*.py` files

## Common Options

### Verbose Output
```bash
python -m pytest tests/ -v
```

### Show Print Statements
```bash
python -m pytest tests/ -v -s
```

### Stop on First Failure
```bash
python -m pytest tests/ -x
```

### Run Last Failed Tests Only
```bash
python -m pytest tests/ --lf
```

### Run Tests in Parallel (if pytest-xdist installed)
```bash
python -m pytest tests/ -n auto
```

### Show Test Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Generate HTML Coverage Report
```bash
python -m pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Markers

Tests can be marked with the following categories:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.mcp` - MCP-related tests
- `@pytest.mark.rag` - RAG-related tests
- `@pytest.mark.agent` - Agent-related tests
- `@pytest.mark.llm` - LLM provider tests
- `@pytest.mark.memory` - Memory system tests
- `@pytest.mark.slow` - Slow running tests

## Examples

### Run Authentication Tests Only
```bash
python -m pytest tests/integration/api/test_auth_api.py -v
```

### Run All API Tests
```bash
python -m pytest tests/integration/api/ -v
```

### Run Tests Matching a Pattern
```bash
python -m pytest tests/ -k "auth" -v
python -m pytest tests/ -k "login" -v
```

### Run Tests and Generate JUnit XML Report
```bash
python -m pytest tests/ --junitxml=test-results.xml
```

## Troubleshooting

### Tests Fail Due to Missing Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt  # If exists
```

### Tests Fail Due to Missing Environment Variables
Create a `.env` file or set environment variables:
```bash
# Required for authentication tests
JWT_SECRET_KEY=your-secret-key-here

# Required for LLM tests
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
DEEPSEEK_API_KEY=your-key-here
```

### Tests Timeout
Increase timeout in `pytest.ini` or use:
```bash
python -m pytest tests/ --timeout=60
```

## Best Practices

1. **Run tests before committing**: Always run the full test suite before committing changes
2. **Run relevant tests during development**: Run specific test categories while developing features
3. **Check coverage**: Ensure new code has adequate test coverage
4. **Fix failing tests**: Never commit code with failing tests
5. **Write tests for new features**: Add tests for any new functionality

## Continuous Integration

For CI/CD pipelines, use:
```bash
python -m pytest tests/ -v --junitxml=test-results.xml --cov=src --cov-report=xml
```

This generates:
- JUnit XML report for test results
- Coverage XML report for coverage tracking

