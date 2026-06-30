param(
    [ValidateSet("smoke", "full")]
    [string]$Profile = "smoke",
    [int]$TimeoutSeconds = 300,
    [switch]$SkipHealthCheck = $false,
    [switch]$SkipRag = $false
)

$ErrorActionPreference = "Stop"

function Invoke-Kubectl {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & kubectl @Args
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Scale-Deployment {
    param(
        [string]$Name,
        [string]$Namespace = "default",
        [int]$Replicas = 1
    )
    Write-Host "Scaling $Namespace/$Name to $Replicas..." -ForegroundColor Cyan
    Invoke-Kubectl scale "deployment/$Name" --namespace $Namespace --replicas $Replicas
}

function Wait-Deployment {
    param(
        [string]$Name,
        [string]$Namespace = "default"
    )
    Write-Host "Waiting for rollout: $Namespace/$Name" -ForegroundColor Cyan
    Invoke-Kubectl rollout status "deployment/$Name" --namespace $Namespace --timeout "${TimeoutSeconds}s"
}

function Set-DeploymentResources {
    param(
        [string]$Name,
        [string]$Namespace,
        [string]$Requests,
        [string]$Limits
    )
    Write-Host "Setting resources for $Namespace/$Name..." -ForegroundColor Cyan
    Invoke-Kubectl set resources "deployment/$Name" --namespace $Namespace --requests $Requests --limits $Limits
}

function Assert-Endpoint {
    param(
        [string]$Name,
        [string]$Namespace = "default"
    )
    $addresses = ""
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        $addresses = kubectl get endpointslice --namespace $Namespace `
            --selector "kubernetes.io/service-name=$Name" `
            -o jsonpath='{.items[*].endpoints[*].addresses[*]}' 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($addresses)) {
            Write-Host "Endpoint OK: $Namespace/$Name -> $addresses" -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 5
    }
    throw "Service $Namespace/$Name has no endpoints."
}

function Invoke-HealthCheck {
    $ip = kubectl get service ai-tool-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
    if ([string]::IsNullOrWhiteSpace($ip)) {
        throw "ai-tool-service has no external LoadBalancer IP."
    }

    $url = "http://$ip/api/health"
    Write-Host "Checking $url..." -ForegroundColor Cyan
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
            if ($response.StatusCode -eq 200) {
                Write-Host "Health check OK: $url" -ForegroundColor Green
                return
            }
        } catch {
            if ($attempt -eq 6) {
                throw
            }
        }
        Start-Sleep -Seconds 5
    }
    throw "Health check failed for $url."
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting GCP Runtime Profile: $Profile" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-DeploymentResources `
    -Name "redis" `
    -Namespace "default" `
    -Requests "cpu=50m,memory=128Mi,ephemeral-storage=1Gi" `
    -Limits "cpu=250m,memory=256Mi,ephemeral-storage=1Gi"

if (-not $SkipRag) {
    Set-DeploymentResources `
        -Name "rag-service" `
        -Namespace "rag-service" `
        -Requests "cpu=100m,memory=512Mi,ephemeral-storage=1Gi" `
        -Limits "ephemeral-storage=1Gi"
}

$requiredDeployments = @(
    @{ Name = "redis"; Namespace = "default" },
    @{ Name = "ai-tool"; Namespace = "default" },
    @{ Name = "celery-worker"; Namespace = "default" },
    @{ Name = "ai-gateway"; Namespace = "ai-gateway" },
    @{ Name = "ai-gateway-kong"; Namespace = "ai-gateway" }
)

if (-not $SkipRag) {
    $requiredDeployments += @{ Name = "rag-service"; Namespace = "rag-service" }
}

if ($Profile -eq "full") {
    $requiredDeployments += @(
        @{ Name = "prometheus"; Namespace = "default" },
        @{ Name = "grafana"; Namespace = "default" },
        @{ Name = "ai-sre-observability"; Namespace = "default" }
    )
}

foreach ($deployment in $requiredDeployments) {
    Scale-Deployment -Name $deployment.Name -Namespace $deployment.Namespace
}

foreach ($deployment in $requiredDeployments) {
    Wait-Deployment -Name $deployment.Name -Namespace $deployment.Namespace
}

Assert-Endpoint -Name "redis-service"
Assert-Endpoint -Name "ai-tool-service"
Assert-Endpoint -Name "ai-gateway" -Namespace "ai-gateway"
Assert-Endpoint -Name "ai-gateway-kong" -Namespace "ai-gateway"
if (-not $SkipRag) {
    Assert-Endpoint -Name "rag-service" -Namespace "rag-service"
} else {
    Write-Host "Skipping rag-service endpoint check because -SkipRag was set." -ForegroundColor Yellow
}

if ($Profile -eq "full") {
    Assert-Endpoint -Name "prometheus-service"
    Assert-Endpoint -Name "grafana-service"
    Assert-Endpoint -Name "ai-sre-observability"
}

if (-not $SkipHealthCheck) {
    Invoke-HealthCheck
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Runtime profile '$Profile' is ready." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
