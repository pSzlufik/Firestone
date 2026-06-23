# Creates a Desktop shortcut "Firestone" you can pin to the taskbar.
# Points at Firestone.exe if it exists, otherwise at pythonw launcher.pyw.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $here "Firestone.exe"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Firestone.lnk"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
if (Test-Path $exe) {
    $sc.TargetPath = $exe
} else {
    $pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $pyw) { Write-Error "pythonw not found and no Firestone.exe; build the exe first."; exit 1 }
    $sc.TargetPath = $pyw
    $sc.Arguments = "`"$(Join-Path $here 'launcher.pyw')`""
}
$sc.WorkingDirectory = $here
$sc.IconLocation = "$exe, 0"
$sc.Save()
Write-Host "Created shortcut: $lnk"
Write-Host "To pin: right-click the shortcut -> Show more options -> Pin to taskbar."
