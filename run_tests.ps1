# PowerShell script to run all tests with timing and generate reports
# Usage: .\run_tests.ps1 [--category <category_name>] [--parallel] [--workers <n>]

param(
    [string]$Category = "",
    [switch]$Parallel = $false,
    [int]$Workers = 0
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please install Python and ensure it's in your PATH." -ForegroundColor Red
    exit 1
}

# Choose test runner (parallel or sequential)
$testScript = if ($Parallel) { 
    "scripts/run_tests_with_timing_parallel.py" 
} else { 
    "scripts/run_tests_with_timing.py" 
}

# Build command arguments
$args = @()
if ($Category -ne "") {
    Write-Host "Running tests for category: $Category" -ForegroundColor Yellow
    $args += "--category", $Category
} else {
    Write-Host "Running all test categories..." -ForegroundColor Yellow
}

if ($Parallel) {
    Write-Host "Using parallel execution mode" -ForegroundColor Cyan
    if ($Workers -gt 0) {
        $args += "--workers", $Workers
        Write-Host "Using $Workers workers per category" -ForegroundColor Cyan
    }
}

# Run tests
python $testScript $args

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Tests completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test reports generated:" -ForegroundColor Cyan
    Write-Host "  - docs/test-reports/TEST_EXECUTION_MASTER_SUMMARY.md" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Some tests failed. Check the output above." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
}

exit $exitCode

