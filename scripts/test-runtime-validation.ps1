# Offline regression checks. Never invokes cloud commands or sends HTTP requests.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/runtime-base-url.ps1"
function Assert($Condition, $Message) {
    if (-not $Condition) { throw $Message }
}
foreach ($url in @('http://requirement.example.com', 'https://requirement.example.com/', 'http://localhost:8080/')) {
    Assert ((Resolve-RuntimeBaseUrl $url) -eq $url.TrimEnd('/')) "URL changed: $url"
}
foreach ($url in @('', 'host-only', 'ftp://example.com', 'http://user:pass@example.com', 'http://example.com/api', 'http://example.com?x=1', 'http://example.com#x', 'http://example.com?', 'http://example.com#', "http://example.com`n")) {
    $rejected = $false
    try { Resolve-RuntimeBaseUrl $url | Out-Null } catch { $rejected = $true }
    Assert $rejected "Accepted invalid URL: $url"
}
$asts = @{}
foreach ($name in @('runtime-base-url', 'start-gcp-runtime', 'deploy-gcp-runtime', 'test-runtime-validation')) {
    $tokens = $null
    $errors = $null
    $asts[$name] = [Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot/$name.ps1", [ref]$tokens, [ref]$errors)
    Assert ($errors.Count -eq 0) "PowerShell syntax errors in $name : $errors"
}
# Extract only the health function: executing the start script would scale workloads.
$health = $asts['start-gcp-runtime'].Find({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-HealthCheck'
}, $true)
Invoke-Expression $health.Extent.Text
function kubectl { throw 'Cloud command attempted by offline test' }
function gcloud { throw 'Cloud command attempted by offline test' }
function Start-Sleep { }
$script:requests = @()
function Invoke-WebRequest {
    param($Uri, [switch]$UseBasicParsing, $TimeoutSec)
    $script:requests += $Uri
    if ($script:requests.Count -lt 3) { throw 'Simulated temporary failure' }
    return @{ StatusCode = 200 }
}
$BaseUrl = Resolve-RuntimeBaseUrl 'https://requirement.example.com/'
Invoke-HealthCheck
Assert ($requests.Count -eq 3) 'Health check did not retry'
Assert (@($requests | Where-Object { $_ -ne 'https://requirement.example.com/api/health' }).Count -eq 0) 'Hostname or scheme lost'
function Invoke-WebRequest { return @{ StatusCode = 503 } }
$failed = $false
try { Invoke-HealthCheck } catch { $failed = $true }
Assert $failed 'Non-200 health check did not fail'
foreach ($name in @('start-gcp-runtime', 'deploy-gcp-runtime')) {
    $failed = $false
    try { & "$PSScriptRoot/$name.ps1" -BaseUrl '' } catch {
        Assert ($_.Exception.Message -like 'Set -BaseUrl*') 'Cloud command reached before URL validation'
        $failed = $true
    }
    Assert $failed "$name accepted a missing URL"
    $text = Get-Content "$PSScriptRoot/$name.ps1" -Raw
    Assert (-not $text.Contains('status.loadBalancer')) "$name retains LoadBalancer dependency"
}
$deploy = Get-Content "$PSScriptRoot/deploy-gcp-runtime.ps1" -Raw
Assert ($deploy.Contains('-BaseUrl $BaseUrl')) 'Deploy script does not forward URL'
$start = Get-Content "$PSScriptRoot/start-gcp-runtime.ps1" -Raw
Assert ($start.Contains('Invoke-Kubectl rollout status') -and $start.Contains('Assert-Endpoint -Name "ai-tool-service"')) 'Rollout/endpoint checks removed'
$cd = Get-Content "$root/.github/workflows/cd.yml" -Raw
Assert (-not $cd.Contains('EXTERNAL_IP') -and -not $cd.Contains('status.loadBalancer')) 'CD retains LoadBalancer dependency'
foreach ($path in @('health', 'auth/login', 'chat')) {
    Assert ($cd.Contains('"${BASE_URL}/api/' + $path + '"')) "CD URL missing for $path"
}
Assert ($cd.IndexOf('Validate gateway base URL') -lt $cd.IndexOf('Authenticate to GCP')) 'CD validates after cloud access'
Assert ($cd.Contains('kubectl rollout status') -and $cd.Contains('kubectl get endpointslice')) 'CD rollout/endpoint checks missing'
foreach ($workflow in Get-ChildItem "$root/.github/workflows/*.yml") {
    $text = Get-Content $workflow.FullName -Raw
    Assert ($text -match '(?m)^on:\s*\r?\n  workflow_dispatch:' -and $text -notmatch '(?m)^  (push|pull_request|workflow_run|schedule|repository_dispatch):') "Automatic workflow trigger in $workflow"
}
Write-Host 'PASS: URL validation, mocked health retries/failure, preflight, syntax, forwarding, endpoint/rollout checks, and manual-only workflows.'
