# Botni Windows'da avtomatik ishga tushadigan qilish (Task Scheduler).
# Ishga tushirish: faylga o'ng tugma -> "Run with PowerShell"
# Agar "running scripts is disabled" desa, avval PowerShell'da:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$bat  = Join-Path $root "deploy\windows\run.bat"
$name = "TelegramPhotoBot"

if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host ".env fayli topilmadi: $root" -ForegroundColor Red
    exit 1
}

# Birinchi safar venv yaratish (oynada ko'rinadi, keyin fon rejimida ishlaydi)
if (-not (Test-Path (Join-Path $root "venv"))) {
    Write-Host "Kutubxonalar o'rnatilmoqda..."
    & py -3 -m venv (Join-Path $root "venv")
    & (Join-Path $root "venv\Scripts\python.exe") -m pip install -q -r (Join-Path $root "requirements.txt")
}

$action    = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`"" -WorkingDirectory $root
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings  = New-ScheduledTaskSettingsSet `
    -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
# S4U: parol so'ramaydi, oynasiz fon rejimida ishlaydi
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Start-ScheduledTask -TaskName $name

# Noutbuk zaryadda turganda uxlamasin (displey o'chishi mumkin)
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

Write-Host ""
Write-Host "O'rnatildi: '$name' vazifasi tizimga kirganda ishga tushadi, to'xtasa 1 daqiqada qayta ishga tushadi." -ForegroundColor Green
Write-Host "Log: $root\bot.log"
Write-Host "To'xtatish:  Stop-ScheduledTask -TaskName $name"
Write-Host "Holat:       Get-ScheduledTask -TaskName $name | Get-ScheduledTaskInfo"
