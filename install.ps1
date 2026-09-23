#Requires -Version 5.1
<#
.SYNOPSIS
  Installs the Cozy Autumn theme (wallpaper slideshow, orange accent, dark mode,
  sound scheme, cursor schemes). Use -Apply to switch to it immediately and
  -LockScreen to also set the lock screen picture.
#>
param([switch]$Apply, [switch]$LockScreen)
$ErrorActionPreference = 'Stop'

$Themes = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Themes'
$Root = Join-Path $Themes 'CozyAutumn'
$Walls = Join-Path $Root 'Wallpapers'
$Snd = Join-Path $Root 'Sounds'
$Cur = Join-Path $Root 'Cursors'
$SchemeKey = 'CozyAutumn'
$SchemeName = 'Cozy Autumn'
$Accent = '0XC4D9622B'   # burnt orange (AARRGGBB)

# Running from a repo clone / download: copy the assets into the Windows themes folder first.
$Here = $PSScriptRoot
if ((Resolve-Path $Here).Path.TrimEnd('\') -ne $Root.TrimEnd('\')) {
    foreach ($d in 'Wallpapers', 'Sounds', 'Cursors') {
        if (-not (Test-Path (Join-Path $Here $d))) { throw "Missing folder next to install.ps1: $d" }
    }
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    foreach ($d in 'Wallpapers', 'Sounds', 'Cursors') {
        robocopy (Join-Path $Here $d) (Join-Path $Root $d) /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Copying $d failed (robocopy exit $LASTEXITCODE)" }
    }
    Copy-Item -Path (Join-Path $Here '*.ps1'), (Join-Path $Here '*.md') -Destination $Root -Force
    Write-Host "Copied theme files to $Root"
}

$sounds = [ordered]@{
    '.Default\.Default'                = 'Default'
    '.Default\SystemAsterisk'          = 'Asterisk'
    '.Default\SystemExclamation'       = 'Exclamation'
    '.Default\SystemHand'              = 'Critical'
    '.Default\SystemQuestion'          = 'Question'
    '.Default\SystemNotification'      = 'Notify'
    '.Default\Notification.Default'    = 'Notify'
    '.Default\Notification.IM'         = 'Message'
    '.Default\Notification.SMS'        = 'Message'
    '.Default\Notification.Mail'       = 'Mail'
    '.Default\MailBeep'                = 'Mail'
    '.Default\Notification.Reminder'   = 'Reminder'
    '.Default\DeviceConnect'           = 'DeviceConnect'
    '.Default\DeviceDisconnect'        = 'DeviceDisconnect'
    '.Default\DeviceFail'              = 'DeviceFail'
    '.Default\WindowsUAC'              = 'UAC'
    '.Default\WindowsLogon'            = 'Logon'
    '.Default\WindowsUnlock'           = 'Logon'
    '.Default\WindowsLogoff'           = 'Logoff'
    '.Default\SystemExit'              = 'Logoff'
    '.Default\LowBatteryAlarm'         = 'BatteryLow'
    '.Default\CriticalBatteryAlarm'    = 'BatteryCritical'
    '.Default\PrintComplete'           = 'PrintComplete'
    'Explorer\EmptyRecycleBin'         = 'RecycleBin'
    'Explorer\Navigating'              = 'Navigate'
}

# Order matters for HKCU\Control Panel\Cursors\Schemes
$cursors = [ordered]@{
    Arrow = 'Arrow.cur'; Help = 'Help.cur'; AppStarting = 'Working.ani'; Wait = 'Busy.ani'
    Crosshair = 'Precision.cur'; IBeam = 'Text.cur'; NWPen = 'Handwriting.cur'; No = 'Unavailable.cur'
    SizeNS = 'SizeNS.cur'; SizeWE = 'SizeWE.cur'; SizeNWSE = 'SizeNWSE.cur'; SizeNESW = 'SizeNESW.cur'
    SizeAll = 'Move.cur'; UpArrow = 'Alternate.cur'; Hand = 'Link.cur'; Pin = 'Pin.cur'; Person = 'Person.cur'
}

foreach ($p in $Walls, $Snd, $Cur) { if (-not (Test-Path $p)) { throw "Missing folder: $p" } }
$first = Get-ChildItem $Walls -Filter *.jpg | Sort-Object Name | Select-Object -First 1
if (-not $first) { throw "No wallpapers found in $Walls" }

# --- register sound scheme -------------------------------------------------
New-Item -Path "HKCU:\AppEvents\Schemes\Names\$SchemeKey" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\AppEvents\Schemes\Names\$SchemeKey" -Name '(default)' -Value $SchemeName
foreach ($e in $sounds.GetEnumerator()) {
    $k = "HKCU:\AppEvents\Schemes\Apps\$($e.Key)\$SchemeKey"
    New-Item -Path $k -Force | Out-Null
    Set-ItemProperty -Path $k -Name '(default)' -Value (Join-Path $Snd "$($e.Value).wav")
}

# --- register cursor schemes (standard / large / extra large) ---------------
New-Item -Path 'HKCU:\Control Panel\Cursors\Schemes' -Force | Out-Null
foreach ($v in @(@{ Sub = ''; Name = $SchemeName }, @{ Sub = 'Large'; Name = "$SchemeName (large)" }, @{ Sub = 'ExtraLarge'; Name = "$SchemeName (extra large)" })) {
    $dir = if ($v.Sub) { Join-Path $Cur $v.Sub } else { $Cur }
    if (-not (Test-Path (Join-Path $dir 'Arrow.cur'))) { continue }
    $list = ($cursors.Values | ForEach-Object { Join-Path $dir $_ }) -join ','
    Set-ItemProperty -Path 'HKCU:\Control Panel\Cursors\Schemes' -Name $v.Name -Value $list
}

# --- write the .theme file ---------------------------------------------------
$sb = [System.Text.StringBuilder]::new()
$null = $sb.AppendLine('[Theme]')
$null = $sb.AppendLine("DisplayName=$SchemeName")
$null = $sb.AppendLine('ThemeId={6C1D4A52-8E3F-4B7A-9C2D-A7F0C0FFEE42}')
$null = $sb.AppendLine()
$null = $sb.AppendLine('[Control Panel\Desktop]')
$null = $sb.AppendLine("Wallpaper=$($first.FullName)")
$null = $sb.AppendLine('TileWallpaper=0')
$null = $sb.AppendLine('WallpaperStyle=10')
$null = $sb.AppendLine('Pattern=')
$null = $sb.AppendLine()
$null = $sb.AppendLine('[Slideshow]')
$null = $sb.AppendLine('Interval=1800000')
$null = $sb.AppendLine('Shuffle=1')
$null = $sb.AppendLine("ImagesRootPath=$Walls")
$null = $sb.AppendLine()
$null = $sb.AppendLine('[VisualStyles]')
$null = $sb.AppendLine('Path=%ResourceDir%\Themes\Aero\Aero.msstyles')
$null = $sb.AppendLine('ColorStyle=NormalColor')
$null = $sb.AppendLine('Size=NormalSize')
$null = $sb.AppendLine('AutoColorization=0')
$null = $sb.AppendLine("ColorizationColor=$Accent")
$null = $sb.AppendLine('SystemMode=Dark')
$null = $sb.AppendLine('AppMode=Dark')
$null = $sb.AppendLine()
$null = $sb.AppendLine('[Control Panel\Colors]')
$null = $sb.AppendLine('Hilight=217 98 43')
$null = $sb.AppendLine('HilightText=255 255 255')
$null = $sb.AppendLine('HotTrackingColor=217 98 43')
$null = $sb.AppendLine('MenuHilight=217 98 43')
$null = $sb.AppendLine()
$null = $sb.AppendLine('[Control Panel\Cursors]')
foreach ($c in $cursors.GetEnumerator()) { $null = $sb.AppendLine("$($c.Key)=$(Join-Path $Cur $c.Value)") }
$null = $sb.AppendLine("DefaultValue=$SchemeName")
$null = $sb.AppendLine()
$null = $sb.AppendLine('[Sounds]')
$null = $sb.AppendLine("SchemeName=$SchemeName")
$null = $sb.AppendLine()
foreach ($e in $sounds.GetEnumerator()) {
    $null = $sb.AppendLine("[AppEvents\Schemes\Apps\$($e.Key)]")
    $null = $sb.AppendLine("DefaultValue=$(Join-Path $Snd "$($e.Value).wav")")
    $null = $sb.AppendLine()
}
$null = $sb.AppendLine('[MasterThemeSelector]')
$null = $sb.AppendLine('MTSM=RJSPBS')

$themeFile = Join-Path $Themes 'CozyAutumn.theme'
$text = $sb.ToString()
# Plain ASCII like the built-in themes; fall back to UTF-16 (also supported) if a path has non-ASCII characters.
$enc = if ($text -match '[^\x00-\x7F]') { [System.Text.UnicodeEncoding]::new($false, $true) } else { [System.Text.Encoding]::ASCII }
[System.IO.File]::WriteAllText($themeFile, $text, $enc)
Remove-Item -LiteralPath (Join-Path $Themes 'Cozy Autumn.theme') -Force -ErrorAction SilentlyContinue
Write-Host "Theme written: $themeFile"
Write-Host "Wallpapers: $((Get-ChildItem $Walls -Filter *.jpg).Count)"

if ($Apply) {
    # A hung Settings process makes OpenThemeAction fail silently, so close it first.
    Get-Process SystemSettings -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Process "$env:SystemRoot\system32\rundll32.exe" -ArgumentList "$env:SystemRoot\system32\themecpl.dll,OpenThemeAction $themeFile"
    Write-Host 'Applying theme...'
}

if ($LockScreen) {
    & (Join-Path $Root 'set-lockscreen.ps1') -Image (Join-Path $Walls 'bi-501-vermont-fall-foliage.jpg')
}
