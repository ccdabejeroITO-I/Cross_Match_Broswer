# CrossMatch v6.32.91 - Windows 11 Docker Desktop launcher/stopper + safe version upgrades.
# Built-in Windows PowerShell 5.1; no Python on Windows host is required.
# No Docker context changes, destructive cleanup, or volume removal.
[CmdletBinding()]
param(
    [ValidateSet('Start','Stop')][string]$Action = 'Start'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Join-Path $root 'docker-compose.yml'
$expectedVersion = '6.32.91'
$script:dockerExe = $null
Set-Location -LiteralPath $root

function Info([string]$message) { Write-Host ('[CrossMatch] ' + $message) }
function Failure([string]$message, [int]$code = 1) {
    Write-Host ''
    Write-Host ('[ERROR] ' + $message) -ForegroundColor Red
    exit $code
}
function Setting([string]$key, [string]$fallback) {
    $processValue = [Environment]::GetEnvironmentVariable($key, 'Process')
    if (-not [string]::IsNullOrWhiteSpace($processValue)) { return $processValue.Trim() }
    $envPath = Join-Path $root '.env'
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in [IO.File]::ReadAllLines($envPath)) {
            if ($line -match '^\s*' + [regex]::Escape($key) + '\s*=\s*(.*?)\s*$') {
                return $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
    return $fallback
}
function SecondsSetting([string]$name, [int]$default, [int]$minimum, [int]$maximum) {
    $value = Setting $name ($default.ToString())
    $number = 0
    if (-not [int]::TryParse($value, [ref]$number) -or $number -lt $minimum -or $number -gt $maximum) {
        Failure "$name must be an integer between $minimum and $maximum."
    }
    return $number
}
function PortSetting([string]$name, [string]$fallback) {
    $value = Setting $name $fallback
    $port = 0
    if (-not [int]::TryParse($value, [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
        Failure "Invalid $name in .env or the Windows environment: $value"
    }
    return $port
}
function DesktopPath {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:ProgramFiles) { $candidates.Add((Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe')) }
    if ($env:LOCALAPPDATA) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe'))
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Docker\Docker Desktop.exe'))
    }
    foreach ($registry in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Docker Desktop',
                          'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Docker Desktop')) {
        try {
            $install = (Get-ItemProperty -LiteralPath $registry -ErrorAction Stop).InstallLocation
            if ($install) { $candidates.Add((Join-Path $install 'Docker Desktop.exe')) }
        } catch { }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).ProviderPath
        }
    }
    return $null
}
function Docker([string[]]$arguments) {
    # PowerShell 5.1 wraps stderr from failed native commands as error records.
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $message = (& $script:dockerExe @arguments 2>&1 | Out-String).Trim()
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 1 }
        return @{ Code = [int]$code; Output = [string]$message }
    } finally { $ErrorActionPreference = $oldPreference }
}
function Compose([string[]]$arguments) {
    $parts = @('compose', '-f', $composeFile) + $arguments
    return Docker $parts
}
function EngineOS {
    $r = Docker @('info', '--format', '{{.OSType}}')
    if ($r.Code -ne 0) { return $null }
    return $r.Output.Trim().ToLowerInvariant()
}
function HasLinuxEngine {
    $os = EngineOS
    if ($os -eq 'windows') {
        Failure 'Docker Desktop is in Windows Containers mode. In the Docker Desktop tray menu choose Switch to Linux containers; this script will not change the mode.'
    }
    return ($os -eq 'linux')
}
function DockerDesktopReady([string]$desktopExe, [int]$startupTimeout) {
    if (HasLinuxEngine) { Info 'Docker Linux Engine: CONNECTED'; return }
    if (-not $desktopExe) {
        Failure 'Docker Engine is unreachable and Docker Desktop was not found in common installation folders. Install/start Docker Desktop (Linux Containers) manually and retry.'
    }
    $desktopProcess = @(Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue)
    if ($desktopProcess.Count -eq 0) {
        Info "Docker Desktop is closed. Launching: $desktopExe"
        try { Start-Process -FilePath $desktopExe -ErrorAction Stop | Out-Null }
        catch { Failure ('Cannot start Docker Desktop: ' + $_.Exception.Message + '. Launch it manually.') }
    } else {
        Info 'Docker Desktop is running, but its engine is not ready yet.'
    }
    Info "Waiting up to $startupTimeout seconds for the Linux Engine..."
    $until = [DateTime]::UtcNow.AddSeconds($startupTimeout)
    $tick = 0
    while ([DateTime]::UtcNow -lt $until) {
        Start-Sleep -Seconds 3
        if (HasLinuxEngine) { Info 'Docker Linux Engine: CONNECTED'; return }
        $tick++
        if (($tick % 5) -eq 0) { Info 'Waiting for Docker Desktop / WSL2 engine...' }
    }
    $ctx = Docker @('context','show')
    $contextName = if ($ctx.Code -eq 0) { $ctx.Output } else { 'unknown' }
    Failure "Docker Linux Engine did not become available after $startupTimeout seconds. Context: $contextName. Open Docker Desktop, check Engine running and Linux Containers, and check WSL2 status with 'wsl --status'. No settings were changed."
}
function ComposeService([string]$service) {
    $r = Compose @('ps','-a','-q', $service)
    if ($r.Code -ne 0) { Failure ('Cannot inspect CrossMatch containers: ' + $r.Output) }
    $ids = @($r.Output -split '\s+' | Where-Object { $_.Trim() -match '^[a-fA-F0-9]{12,64}$' })
    if ($ids.Count -eq 0) { return $null }
    return $ids[0]
}
function ContainerState([string]$id) {
    if (-not $id) { return @{ Running = $false; Healthy = $false; Status = 'missing' } }
    $r = Docker @('inspect','--format','{{.State.Running}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}', $id)
    if ($r.Code -ne 0) { return @{ Running = $false; Healthy = $false; Status = 'unknown' } }
    $values = $r.Output.Trim() -split '\|',2
    return @{ Running = ($values[0] -eq 'true'); Healthy = ($values.Count -gt 1 -and $values[1] -eq 'healthy'); Status = $r.Output }
}
function RunningWebVersion {
    $r = Compose @('exec','-T','web','python','-c','from config import APP_VERSION; print(APP_VERSION)')
    if ($r.Code -ne 0) { return $null }
    return $r.Output.Trim()
}
# Inspect file-backed job statuses inside the already-running web container.
# If checking fails, upgrades are blocked rather than risking interrupted jobs.
# Docker Compose identifies the project globally, even if this launcher is run
# from a freshly extracted ZIP. A project label alone is not evidence that the
# live container uses this folder's ./database. Inspect actual bind mounts before
# proceeding, and do not rely on Go templates whose quote escaping varies with
# Windows PowerShell 5.1's native-argument handling.
function ContainerInspection([string]$containerId) {
    $response = Docker @('inspect', $containerId)
    if ($response.Code -ne 0) {
        Failure ('Cannot inspect existing CrossMatch container. No update attempted. Docker: ' + $response.Output)
    }
    try {
        $items = @(ConvertFrom-Json -InputObject $response.Output)
        if ($items.Count -ne 1 -or $null -eq $items[0].Mounts) {
            Failure 'Docker returned incomplete container inspection data. No update attempted.'
        }
        return $items[0]
    } catch {
        Failure ('Cannot parse Docker container inspection. No update attempted: ' + $_.Exception.Message)
    }
}
function ContainerLabel([object]$inspect, [string]$key) {
    if ($null -eq $inspect.Config -or $null -eq $inspect.Config.Labels) { return '' }
    $entry = $inspect.Config.Labels.PSObject.Properties[$key]
    if ($null -eq $entry) { return '' }
    return [string]$entry.Value
}
function HostPath([string]$path) {
    if ([string]::IsNullOrWhiteSpace($path)) { return $null }
    $slash = $path.Trim().Replace('\', '/')
    # Docker Desktop can report either Windows paths or Linux-side host mounts.
    if ($slash -match '^/run/desktop/mnt/host/([a-zA-Z])/(.*)$' -or
        $slash -match '^/host_mnt/([a-zA-Z])/(.*)$' -or
        $slash -match '^/mnt/host/([a-zA-Z])/(.*)$' -or
        $slash -match '^/mnt/([a-zA-Z])/(.*)$') {
        $slash = $Matches[1].ToUpperInvariant() + ':/' + $Matches[2]
    }
    if ($slash -notmatch '^[a-zA-Z]:/' -and $slash -notmatch '^//[^/]+/[^/]+') {
        return $null  # An unrecognized path is NOT accepted as proof of data safety.
    }
    try {
        return [IO.Path]::GetFullPath($slash.Replace('/', '\')).TrimEnd('\', '/')
    } catch { return $null }
}
function VerifyProjectDirectory([string]$containerId, [string]$service) {
    if (-not $containerId) { return }
    $item = ContainerInspection $containerId
    $expectedProject = 'crossmatch_browser_v631'
    $actualProject = ContainerLabel $item 'com.docker.compose.project'
    $actualService = ContainerLabel $item 'com.docker.compose.service'
    if ($actualProject -ne $expectedProject -or $actualService -ne $service) {
        Failure "Existing container identity could not be verified (project=$actualProject; service=$actualService). No containers were modified."
    }
    $dest = if ($service -eq 'web') { '/app/database' } else { '/etc/nginx/certs' }
    $subdir = if ($service -eq 'web') { 'database' } else { 'certificates' }
    $volume = @($item.Mounts | Where-Object { $_.Destination -eq $dest })
    if ($volume.Count -ne 1 -or $volume[0].Type -ne 'bind') {
        Failure "Cannot confirm persistent $subdir bind mount ($dest) of the existing container. No update was attempted."
    }
    $liveSource = [string]$volume[0].Source
    $livePath = HostPath $liveSource
    $localPath = HostPath (Join-Path $root $subdir)
    if (-not $livePath -or -not $localPath) {
        Failure "Cannot safely compare the existing $subdir mount '$liveSource' with local folder '$root'. No update attempted. Copy updated application files into the original CrossMatch installation directory."
    }
    if (-not [string]::Equals($livePath, $localPath, [StringComparison]::OrdinalIgnoreCase)) {
        $oldRootLabel = ContainerLabel $item 'com.docker.compose.project.working_dir'
        Info "Existing CrossMatch $subdir mount: $livePath"
        Info "This launcher's $subdir folder: $localPath"
        if (-not [string]::IsNullOrWhiteSpace($oldRootLabel)) { Info "Original Compose working directory: $oldRootLabel" }
        Failure "Different CrossMatch data folder detected. DO NOT update from this extracted folder. Copy the new application files into the ORIGINAL CrossMatch folder shown above, preserving its database, certificates and .env. No containers were stopped."
    }
    $workLabel = ContainerLabel $item 'com.docker.compose.project.working_dir'
    if ([string]::IsNullOrWhiteSpace($workLabel)) {
        Info "Verified existing CrossMatch $subdir mount matches this installation (legacy Compose folder label missing)."
    } else {
        $labelPath = HostPath $workLabel
        if ($labelPath -and -not [string]::Equals($labelPath, (HostPath $root), [StringComparison]::OrdinalIgnoreCase)) {
            Info "Docker's working-directory label differs, but the actual $subdir bind mount matches this installation."
        }
    }
}

function ActiveJobCount {
    $code = 'import json; from config import CACHE_ROOT; files = list(CACHE_ROOT.glob("session_*/working/*/job.json")); print(sum(1 for p in files if json.loads(p.read_text(encoding="utf-8")).get("state") in ("queued", "running")))'
    $result = Compose @('exec', '-T', 'web', 'python', '-c', $code)
    if ($result.Code -ne 0 -or $result.Output -notmatch '^\d+$') {
        Failure ('Cannot reliably check active CrossMatch jobs. No upgrade was made. Inspect running jobs in the web app before manually stopping CrossMatch. Diagnostic: ' + $result.Output)
    }
    return [int]$result.Output
}
function ApproveVersionUpgrade([string]$installed, [string]$wanted) {
    $old = $null
    $new = $null
    if (-not [version]::TryParse($installed, [ref]$old) -or -not [version]::TryParse($wanted, [ref]$new)) {
        Failure "Unrecognized running/app version ($installed / $wanted). No automatic update was attempted."
    }
    if ($old -ge $new) {
        Failure "Running CrossMatch version '$installed' is the same as or newer than the requested update '$wanted'. Downgrades are blocked."
    }
    Info "Running version: $installed; source folder version: $wanted."
    Info 'This update requires stopping and recreating ONLY this CrossMatch Compose project.'
    $jobs = ActiveJobCount
    if ($jobs -gt 0) {
        Failure "$jobs queued/running CrossMatch job(s) detected. Finish them before upgrading. No container was stopped."
    }
    Info 'No queued or running jobs were found in the saved CrossMatch job statuses.'
    Write-Host ''
    Write-Host 'IMPORTANT: Confirm there are no active processing jobs in the browser.' -ForegroundColor Yellow
    Write-Host 'This will STOP CrossMatch briefly, then REBUILD and START the new version.' -ForegroundColor Yellow
    Write-Host 'Database, uploads, certificates, .env and named volumes will NOT be deleted.' -ForegroundColor Yellow
    Write-Host 'Other Docker projects will NOT be stopped.' -ForegroundColor Yellow
    $answer = ''
    try { $answer = Read-Host 'Type UPDATE to proceed; press Enter to cancel' }
    catch { Failure 'Interactive confirmation unavailable; no upgrade performed. Run START_DOCKER.bat in a console.' }
    if ($answer.Trim() -ne 'UPDATE') {
        Failure 'Upgrade cancelled. Existing containers were left running.' 2
    }
    Info 'Stopping only this CrossMatch Compose project before rebuilding.'
    $stop = Compose @('stop')
    if ($stop.Code -ne 0) { Failure ('Could not stop CrossMatch safely: ' + $stop.Output) }
    $stoppedWeb = ContainerState (ComposeService 'web')
    $stoppedProxy = ContainerState (ComposeService 'proxy')
    if ($stoppedWeb.Running -or $stoppedProxy.Running) {
        Failure 'Some CrossMatch containers are still running. Upgrade aborted; no volumes were removed.'
    }
    Info 'Old CrossMatch containers stopped. Persistent data and Docker volumes retained.'
    return $true
}

function Health([int]$httpPort) {
    try {
        $service = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$httpPort/api/health" -TimeoutSec 5 -ErrorAction Stop
        if (-not $service.ok -or $service.version -ne $expectedVersion) { return $false }
        $selftest = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$httpPort/api/selftest" -TimeoutSec 8 -ErrorAction Stop
        return ($selftest.ok -eq $true -and $selftest.engine -ne 'unknown')
    } catch { return $false }
}
# Diagnostics never stop/recreate containers or expose the .env file.
function ShowLogs {
    Info 'CrossMatch container status:'
    $status = Compose @('ps','-a')
    if ($status.Output) { Write-Host $status.Output }
    Info 'Recent WEB backend logs (last 60 lines):'
    $webLog = Compose @('logs','--no-color','--tail','60','web')
    if ($webLog.Output) { Write-Host $webLog.Output }
    Info 'Recent HTTPS PROXY logs (last 25 lines):'
    $proxyLog = Compose @('logs','--no-color','--tail','25','proxy')
    if ($proxyLog.Output) { Write-Host $proxyLog.Output }
}
function HttpDiagnostic([int]$port) {
    $baseUrl = "http://127.0.0.1:$port"
    try {
        $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/health" -TimeoutSec 5 -ErrorAction Stop
        Info ("HTTP backend responds: ok=" + $health.ok + "; version=" + $health.version + "; engine=" + $health.engine)
        if ($health.version -ne $expectedVersion) {
            Info "Expected v$expectedVersion but HTTP backend serves v$($health.version). Check image rebuild and port binding."
        }
    } catch {
        Info ("HTTP health request FAILED: " + $_.Exception.Message)
    }
    try {
        $test = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/selftest" -TimeoutSec 8 -ErrorAction Stop
        $failed = @($test.checks.PSObject.Properties | Where-Object { $_.Value -ne $true } | ForEach-Object { $_.Name })
        Info ("Self-test responds: ok=" + $test.ok + "; failed checks=" + ($failed -join ','))
        if ($test.homepage_error) { Info ("Self-test homepage error: " + $test.homepage_error) }
    } catch {
        Info ("Self-test request FAILED: " + $_.Exception.Message)
    }
}
function HealthStateDiagnostic([string]$service) {
    $id = ComposeService $service
    if (-not $id) { Info "$service container: MISSING"; return }
    $response = Docker @('inspect', $id)
    if ($response.Code -ne 0) { Info ("$service inspection failed: " + $response.Output); return }
    try {
        $data = @(ConvertFrom-Json -InputObject $response.Output)[0]
        $state = $data.State
        $healthStatus = if ($null -ne $state.Health) { $state.Health.Status } else { 'no healthcheck' }
        Info ("$service container: state=" + $state.Status + "; health=" + $healthStatus + "; exit=" + $state.ExitCode + "; restarts=" + $data.RestartCount)
        if ($state.Error) { Info ("$service error: " + $state.Error) }
        if ($null -ne $state.Health) {
            $recent = @($state.Health.Log | Select-Object -Last 2)
            foreach ($entry in $recent) {
                $message = ([string]$entry.Output).Trim()
                if ($message.Length -gt 350) { $message = $message.Substring(0,350) + '...' }
                Info ("$service health check: exit=" + $entry.ExitCode + "; " + $message)
            }
        }
    } catch {
        Info ("$service health inspection unavailable: " + $_.Exception.Message)
    }
}
function ShowStartupDiagnostics([int]$port) {
    Write-Host ''
    Info 'STARTUP DIAGNOSTICS — no containers or files will be removed'
    HealthStateDiagnostic 'web'
    HealthStateDiagnostic 'proxy'
    HttpDiagnostic $port
    ShowLogs
    Write-Host ''
    Info 'Recovery: check WEB traceback in the logs above and verify Docker Desktop memory and ports.'
    Info 'If the HTTP backend works but proxy health fails, port 18090 can still serve the local web app.'
}
function PortListener([int]$port) {
    # Read only: never kill or stop a process using an application port.
    try {
        $connections = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop)
        if ($connections.Count -gt 0) {
            $pidValue = $connections[0].OwningProcess
            $processName = 'unknown'
            try { $processName = (Get-Process -Id $pidValue -ErrorAction Stop).ProcessName } catch { }
            return "port $port is already listening (PID $pidValue, process $processName)"
        }
    } catch {
        # Get-NetTCPConnection might be unavailable; try netstat without changing the OS.
        try {
            $lines = @(netstat.exe -ano -p tcp 2>$null | Select-String (':'+$port+'\s+.*LISTENING'))
            if ($lines.Count -gt 0) { return "port $port is already listening (netstat)" }
        } catch { }
    }
    return $null
}
try {
    Write-Host ''
    Info 'CrossMatch Browser v6.32.91 - Docker control'
    if (-not (Test-Path -LiteralPath $composeFile)) { Failure 'docker-compose.yml is missing from the CrossMatch folder.' }
    $desktopExe = DesktopPath
    $cmd = Get-Command docker.exe -ErrorAction SilentlyContinue
    if ($cmd) { $script:dockerExe = $cmd.Source }
    elseif ($desktopExe) {
        $fallbackExe = Join-Path (Split-Path -Parent $desktopExe) 'resources\bin\docker.exe'
        if (Test-Path -LiteralPath $fallbackExe) { $script:dockerExe = $fallbackExe }
    }
    if (-not $script:dockerExe) {
        if ($desktopExe) { Failure 'Docker Desktop was found but docker.exe CLI is missing or not on PATH. Repair Docker Desktop or add its resources\bin folder to PATH.' }
        Failure 'Docker CLI not found. Install Docker Desktop for Windows with Linux Containers, then reopen this window.'
    }
    Info 'Docker CLI: FOUND'
    Info ('Docker Desktop: ' + $(if ($desktopExe) { 'INSTALLED' } else { 'not detected in usual paths' }))
    if ($Action -eq 'Stop') {
        if (-not (HasLinuxEngine)) {
            Failure 'Docker Engine is unavailable. Cannot verify whether CrossMatch is running; nothing was stopped. Start Docker Desktop manually if you need to check its status.' 2
        }
        Info 'Docker Linux Engine: CONNECTED'
        $composeCheck = Compose @('version')
        if ($composeCheck.Code -ne 0) { Failure ('Docker Compose unavailable: ' + $composeCheck.Output) }
        $webId = ComposeService 'web'; $proxyId = ComposeService 'proxy'
        if ($webId) { VerifyProjectDirectory $webId 'web' }
        if ($proxyId) { VerifyProjectDirectory $proxyId 'proxy' }
        $web = ContainerState $webId; $proxy = ContainerState $proxyId
        if (-not $web.Running -and -not $proxy.Running) {
            Info 'CrossMatch is already stopped (no project containers running). No files were changed.'
            exit 0
        }
        Info 'Stopping CrossMatch project containers only. Persistent data/volumes are retained.'
        $r = Compose @('stop')
        if ($r.Code -ne 0) { Failure ('CrossMatch shutdown failed: ' + $r.Output) }
        $web = ContainerState (ComposeService 'web'); $proxy = ContainerState (ComposeService 'proxy')
        if ($web.Running -or $proxy.Running) {
            Failure 'The stop command returned but some CrossMatch containers are still running. No volumes were deleted.'
        }
        Info 'CrossMatch Containers: STOPPED. Database, uploaded files, results, and Docker volumes retained.'
        exit 0
    }

    $startTimeout = SecondsSetting 'CROSSMATCH_DOCKER_START_TIMEOUT' 120 15 900
    $healthTimeout = SecondsSetting 'CROSSMATCH_HEALTH_TIMEOUT' 180 15 900
    $httpPort = PortSetting 'CROSSMATCH_HTTP_PORT' '18090'
    $httpsPort = PortSetting 'CROSSMATCH_HTTPS_PORT' '18444'
    $composeWait = [Math]::Max(60, [Math]::Min(900, $healthTimeout))
    DockerDesktopReady $desktopExe $startTimeout
    $composeCheck = Compose @('version')
    if ($composeCheck.Code -ne 0) { Failure ('Docker Compose unavailable: ' + $composeCheck.Output) }
    Info 'Docker Compose: AVAILABLE'
    $webId = ComposeService 'web'; $proxyId = ComposeService 'proxy'
    $web = ContainerState $webId; $proxy = ContainerState $proxyId
    # Version upgrades must never accidentally point an existing Compose project
    # at an empty ./database in a newly extracted ZIP folder.
    if ($webId) { VerifyProjectDirectory $webId 'web' }
    if ($proxyId) { VerifyProjectDirectory $proxyId 'proxy' }
    $approvedUpgrade = $false
    if ($web.Running) {
        $actualVersion = RunningWebVersion
        if ([string]::IsNullOrWhiteSpace($actualVersion)) {
            Failure 'The running CrossMatch version could not be determined. No upgrade was attempted. Inspect Docker logs or stop manually after jobs finish.'
        }
        if ($actualVersion -ne $expectedVersion) {
            $approvedUpgrade = ApproveVersionUpgrade $actualVersion $expectedVersion
            # Re-inspect live state after approved stop; never use stale running flags.
            $web = ContainerState (ComposeService 'web')
            $proxy = ContainerState (ComposeService 'proxy')
        }
    }
    # HTTP 18090 is served directly by WEB. Optional HTTPS proxy health must
    # not make a healthy local HTTP application appear broken.
    $alreadyRunning = ($web.Running -and $web.Healthy -and (Health $httpPort))
    if ($alreadyRunning) {
        Info 'CrossMatch is already running and healthy. Skipping build/recreation.'
    } else {
        if (-not $web.Running -and -not $proxy.Running) {
            foreach ($port in @($httpPort, $httpsPort) | Select-Object -Unique) {
                $listener = PortListener $port
                if ($listener) { Failure "Port conflict: $listener. Free the port or change CROSSMATCH_HTTP_PORT/CROSSMATCH_HTTPS_PORT in .env. No unrelated process was terminated." }
            }
        }
        if (-not (Test-Path -LiteralPath (Join-Path $root 'database\crossmatch_web_v631.db'))) {
            Info 'New database detected. Preparing first-admin setup key with the existing generator.'
            $generator = Join-Path $root 'GENERATE_SETUP_KEY.bat'
            if (-not (Test-Path -LiteralPath $generator)) { Failure 'GENERATE_SETUP_KEY.bat is missing.' }
            & cmd.exe /d /c ('"' + $generator + '"')
            if ($LASTEXITCODE -ne 0) { Failure 'First-admin setup key generation failed. Existing .env was not deleted.' }
        }
        if ($web.Running -or $proxy.Running) {
            Info 'Some CrossMatch services are already running. Using --no-recreate to avoid interrupting jobs.'
            $start = Compose @('up','-d','--no-recreate')
        } else {
            if ($approvedUpgrade) {
                Info 'Building and recreating CrossMatch containers after confirmed upgrade. Docker volumes are retained.'
                $start = Compose @('up','-d','--build','--force-recreate')
            } else {
                Info 'Starting CrossMatch using the existing Compose file (first build may need internet).'
                $start = Compose @('up','-d','--build')
            }
        }
        if ($start.Code -ne 0) {
            Write-Host $start.Output
            # Compose can fail when the optional HTTPS proxy fails to start, even
            # if WEB on 18090 is already healthy. Inspect before declaring failure.
            $webOnError = ContainerState (ComposeService 'web')
            if (-not ($webOnError.Running -and $webOnError.Healthy -and (Health $httpPort))) {
                ShowStartupDiagnostics $httpPort
                Failure 'CrossMatch WEB service did not start successfully. See backend errors and container health diagnostics above.'
            }
            Info 'WARNING: Compose reported a service error, but the local HTTP WEB service passed health checks. HTTPS proxy may be unavailable.'
        }
    }
    $until = [DateTime]::UtcNow.AddSeconds($healthTimeout)
    $healthy = $false
    do {
        $web = ContainerState (ComposeService 'web')
        $proxy = ContainerState (ComposeService 'proxy')
        if ($web.Running -and $web.Healthy -and (Health $httpPort)) {
            $healthy = $true; break
        }
        Start-Sleep -Seconds 3
    } while ([DateTime]::UtcNow -lt $until)
    if (-not $healthy) {
        ShowStartupDiagnostics $httpPort
        Failure "HTTP Web health failed after $healthTimeout seconds. CrossMatch is NOT READY. Diagnostics above distinguish container crash, unhealthy backend, port error and version mismatch."
    }
    $actualVersion = RunningWebVersion
    if ($actualVersion -ne $expectedVersion) {
        Failure "Application health responded, but running container version '$actualVersion' does not match '$expectedVersion'. Restart after safely stopping active jobs."
    }
    Write-Host ''
    Write-Host '========================================'
    Write-Host 'CROSSMATCH WEB APPLICATION'
    Write-Host '========================================'
    Write-Host 'Docker Desktop: AVAILABLE'
    Write-Host 'Docker Linux Engine: CONNECTED'
    Write-Host 'Docker Compose: AVAILABLE'
    Write-Host 'CrossMatch WEB Container: RUNNING'
    Write-Host 'HTTP Application Health: HEALTHY'
    $proxyFinal = ContainerState (ComposeService 'proxy')
    if ($proxyFinal.Running -and $proxyFinal.Healthy) {
        Write-Host 'HTTPS Proxy: HEALTHY'
    } else {
        Write-Host 'HTTPS Proxy: NOT READY (local HTTP app still available)' -ForegroundColor Yellow
        Info 'HTTPS at port 18444 may not work until the proxy issue is resolved.'
        HealthStateDiagnostic 'proxy'
    }
    Write-Host ('Version: ' + $expectedVersion)
    Write-Host ''
    Write-Host ('Application URL: http://127.0.0.1:' + $httpPort + '/')
    Write-Host 'CrossMatch is ready.'
    Write-Host '========================================'
    exit 0
} catch {
    Failure ('Unexpected Docker control error: ' + $_.Exception.Message)
}
