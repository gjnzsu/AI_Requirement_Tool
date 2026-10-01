function Resolve-RuntimeBaseUrl {
    param([string]$BaseUrl)
    $uri = $null
    if ([string]::IsNullOrWhiteSpace($BaseUrl) -or $BaseUrl -match '\s|[?#]' -or
        -not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -notin @('http', 'https') -or
        [string]::IsNullOrWhiteSpace($uri.Host) -or
        $uri.UserInfo -or $uri.Query -or $uri.Fragment -or
        $uri.AbsolutePath -ne '/') {
        throw 'Set -BaseUrl or AI_TOOL_BASE_URL to an HTTP(S) origin (for example https://requirement.example.com), without credentials, path, query, or fragment.'
    }
    return $BaseUrl.TrimEnd('/')
}
