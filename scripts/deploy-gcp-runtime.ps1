param(
    [ValidateSet("smoke", "full")]
    [string]$Profile = "smoke",
    [string]$ProjectId = "gen-lang-client-0896070179",
    [string]$Region = "us-central1",
    [string]$Repository = "ai-requirement-tool",
    [string]$ImageName = "ai-requirement-tool",
    [string]$Tag = "",
    [int]$TimeoutSeconds = 300,
    [switch]$SkipBuild = $false,
    [switch]$SkipHealthCheck = $false,
    [switch]$SkipRag = $false
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

if ([string]::IsNullOrWhiteSpace($Tag)) {
    $Tag = "manual-$(Get-Date -Format yyyyMMddHHmmss)"
}

$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying AI Requirement Tool Runtime" -ForegroundColor Cyan
Write-Host "Image: $image" -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $SkipBuild) {
    Write-Host "Submitting Cloud Build..." -ForegroundColor Cyan
    Invoke-Checked gcloud @("builds", "submit", "--tag", $image, ".")
}

Write-Host "Applying base manifests..." -ForegroundColor Cyan
Invoke-Checked kubectl @("apply", "-f", "k8s\pvc.yaml")
Invoke-Checked kubectl @("apply", "-f", "k8s\redis-deployment.yaml")
Invoke-Checked kubectl @("apply", "-f", "k8s\redis-service.yaml")

Write-Host "Applying app manifests with image..." -ForegroundColor Cyan
(Get-Content "k8s\deployment.yaml") -replace "IMAGE_PLACEHOLDER", $image | kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply k8s\deployment.yaml"
}

(Get-Content "k8s\celery-worker-deployment.yaml") -replace "IMAGE_PLACEHOLDER", $image | kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply k8s\celery-worker-deployment.yaml"
}

Invoke-Checked kubectl @("apply", "-f", "k8s\service.yaml")

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptDir "start-gcp-runtime.ps1"
& $startScript -Profile $Profile -TimeoutSeconds $TimeoutSeconds -SkipHealthCheck:$SkipHealthCheck -SkipRag:$SkipRag
if ($LASTEXITCODE -ne 0) {
    throw "$startScript failed with exit code $LASTEXITCODE"
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Image: $image" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
