param([Parameter(Mandatory=$true)][string]$Image)
$ErrorActionPreference = 'Stop'
if ($Image -notmatch ':sha-([a-f0-9]{40})$') {
    throw 'Use the immutable commit tag: USER/bonchorok:sha-FULL_COMMIT_SHA'
}
$sha=$Matches[1]
$env:PYTHONUTF8='1'
$root=Split-Path -Parent $PSScriptRoot
$evidence=Join-Path $root ('artifacts/manual-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
& python (Join-Path $root 'ops/validate_deploy.py') --image $Image --sha $sha --out $evidence
if ($LASTEXITCODE -ne 0) { throw "Deployment or validation failed. See $evidence" }
