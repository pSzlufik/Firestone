# Builds Firestone.exe (the launcher bar) so you can pin it to the taskbar.
# Run from this folder:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "Installing PyInstaller (if needed)..."
py -m pip install --quiet --disable-pip-version-check pyinstaller

Write-Host "Building Firestone.exe..."
py -m PyInstaller --onefile --noconsole --name Firestone `
    --distpath "$here" --workpath "$here\build" --specpath "$here\build" `
    "$here\launcher.pyw"

if (Test-Path "$here\Firestone.exe") {
    Write-Host "`nDone -> $here\Firestone.exe"
    Write-Host "Right-click it -> Pin to taskbar (or run make_shortcut.ps1 for a Desktop shortcut)."
} else {
    Write-Error "Build failed - Firestone.exe was not produced."
}
