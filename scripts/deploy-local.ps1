param(
    [Parameter(Mandatory = $true)][string]$Image,
    [ValidateRange(1024, 65535)][int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
$name = 'bonchorok-local'
$candidate = "$name-candidate"
$backup = "$name-previous"
$label = 'io.bonchorok.managed'

function Docker {
    # A simple function preserves CLI flags such as -a instead of binding them
    # as abbreviations of a PowerShell parameter named Arguments.
    $dockerArgs = $args
    $output = & docker.exe @dockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: $($dockerArgs[0]) (exit $LASTEXITCODE)" }
    return $output
}
function Inspect-Container([string]$Container) {
    $names = @(Docker ps -a --format '{{.Names}}')
    if ($names -notcontains $Container) { return $null }
    $result = (Docker inspect $Container) | ConvertFrom-Json
    return $result[0]
}
function Assert-Managed($Container) {
    if ($Container -and $Container.Config.Labels.$label -ne 'true') {
        throw 'Container name belongs to an unmanaged container. No changes were made to it.'
    }
}
function Wait-Healthy([string]$Container) {
    for ($i = 0; $i -lt 45; $i++) {
        $info = Inspect-Container $Container
        if (-not $info -or -not $info.State.Running) { throw "$Container is not running." }
        if ($info.State.Health.Status -eq 'healthy') { return }
        if ($info.State.Health.Status -eq 'unhealthy') { throw "$Container is unhealthy." }
        Start-Sleep -Seconds 2
    }
    throw "$Container did not become healthy within 90 seconds."
}
function Test-Http([int]$HostPort) {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$HostPort/api/health" -TimeoutSec 10
    if ($response.status -ne 'ok' -or $response.herb_count -ne 601) { throw 'Unexpected health response.' }
    $page = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$HostPort/?herb=sophorae-flos" -TimeoutSec 10
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'app-v2.js') { throw 'Application page check failed.' }
}

$existing = Inspect-Container $name
Assert-Managed $existing
if (Inspect-Container $backup) { throw "Recovery container $backup exists. Review it before another deployment." }
$stale = Inspect-Container $candidate
Assert-Managed $stale
if ($stale) { Docker rm --force $candidate | Out-Host }

# Pull before touching the currently running service.
for ($attempt = 1; $attempt -le 3; $attempt++) {
    try { Docker pull $Image | Out-Host; break }
    catch { if ($attempt -eq 3) { throw }; Start-Sleep -Seconds 5 }
}
$imageId = Docker image inspect --format '{{.Id}}' $Image
$candidateCreated = $false
$oldRenamed = $false
$oldStopped = $false
$newCreated = $false
$committed = $false
try {
    Docker run --detach --name $candidate --label "${label}=true" --publish '127.0.0.1::8000' $imageId | Out-Host
    $candidateCreated = $true
    Wait-Healthy $candidate
    Docker exec $candidate python smoke_test.py | Out-Host
    $info = Inspect-Container $candidate
    Test-Http ([int]$info.NetworkSettings.Ports.'8000/tcp'[0].HostPort)
    Docker rm --force $candidate | Out-Host
    $candidateCreated = $false

    if ($existing) {
        if ($existing.State.Running) { Docker stop $name | Out-Host; $oldStopped = $true }
        Docker rename $name $backup | Out-Host
        $oldRenamed = $true
    }
    Docker run --detach --restart unless-stopped --name $name --label "${label}=true" --publish "127.0.0.1:${Port}:8000" $imageId | Out-Host
    $newCreated = $true
    Wait-Healthy $name
    Docker exec $name python smoke_test.py | Out-Host
    Test-Http $Port
    $committed = $true
    if ($oldRenamed) { Docker rm $backup | Out-Host; $oldRenamed = $false }
    Write-Output "PASS: deployed $Image at http://127.0.0.1:$Port"
} catch {
    $failure = $_
    # Native stderr must not interrupt rollback under Windows PowerShell 5.1.
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & docker.exe logs --tail 80 $candidate 2>&1 | Out-Host
    & docker.exe logs --tail 80 $name 2>&1 | Out-Host
    $ErrorActionPreference = $savedPreference
    if (-not $committed) {
        # docker run may create a container even when port binding fails.
        $failed = Inspect-Container $name
        if ($newCreated -or ($oldRenamed -and $failed) -or (-not $existing -and $failed)) {
            Assert-Managed $failed
            Docker rm --force $name | Out-Host
        }
        if ($oldRenamed) { Docker rename $backup $name | Out-Host }
        if ($oldStopped) {
            Docker start $name | Out-Host
            Wait-Healthy $name
            Test-Http $Port
            Write-Output 'Previous service restored after deployment failure.'
        }
    }
    throw $failure
} finally {
    if ($candidateCreated) { & docker.exe rm --force $candidate | Out-Host }
}
