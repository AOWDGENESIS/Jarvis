# CREATE_SHORTCUT.ps1 - JARVIS OMNI v8.0
# Erstellt Desktop-Verknuepfung mit echtem Arc-Reactor Icon

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BatPath      = Join-Path $ScriptDir "RUN_JARVIS.bat"
$IconIco      = Join-Path $ScriptDir "jarvis_icon.ico"
$Desktop      = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "JARVIS OMNI.lnk"

if (-not (Test-Path $BatPath)) {
    Write-Host "[FEHLER] RUN_JARVIS.bat nicht gefunden."
    exit 1
}

try {
    $WshShell  = New-Object -ComObject WScript.Shell
    $Shortcut  = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath       = $BatPath
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.WindowStyle      = 1
    $Shortcut.Description      = "JARVIS OMNI v8.0 starten"
    if (Test-Path $IconIco) {
        $Shortcut.IconLocation = "$IconIco,0"
    }
    $Shortcut.Save()
    Write-Host "[OK] Desktop-Verknuepfung erstellt: $ShortcutPath"
    exit 0
} catch {
    Write-Host "[FEHLER] $($_.Exception.Message)"
    exit 1
}
