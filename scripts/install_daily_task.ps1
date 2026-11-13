param(
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$At = "09:00"
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $cmd = Get-Command python -ErrorAction Stop
    $python = $cmd.Source
}
$runner = Join-Path $root "scripts\run_daily_update.py"
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $runner + '"') -WorkingDirectory $root
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "ElderAccidentNewsroomDailyUpdate" -Action $action -Trigger $trigger -Settings $settings -Description "Daily RSS metadata + local CSV change monitoring" -Force | Out-Null
Write-Host "등록: ElderAccidentNewsroomDailyUpdate / 매일 $At (Windows PC가 켜져 있고 로그인한 상태 기준)"
Write-Host "즉시 확인: python scripts/run_daily_update.py"
