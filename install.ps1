#Requires -Version 5.1
<#
.SYNOPSIS
  Installs the Cozy Autumn theme (wallpaper slideshow, orange accent, dark mode,
  sound scheme, cursor schemes). Use -Apply to switch to it immediately and
  -LockScreen to also set the lock screen picture. -WallpapersOnly preserves the
  existing theme's other fields. -ValidateOnly performs read-only asset checks.
#>
param([switch]$Apply, [switch]$LockScreen, [switch]$WallpapersOnly, [switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'

$Here = $PSScriptRoot
$manifestPath = Join-Path $Here 'wallpapers.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Missing wallpapers.json. Use the curated collection, not the legacy fetching scripts.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$sourceWalls = Join-Path $Here 'Wallpapers'
$files = @(Get-ChildItem -LiteralPath $sourceWalls -Filter *.jpg -File)
if ($files.Count -eq 0 -or $files.Count -ne @($manifest.photos).Count) { throw 'Wallpaper inventory does not match wallpapers.json.' }
if (@($manifest.photos.file | Select-Object -Unique).Count -ne $files.Count) { throw 'Duplicate wallpaper manifest entries.' }
$credits = Get-Content -LiteralPath (Join-Path $Here 'CREDITS.md') -Raw
Add-Type -AssemblyName System.Drawing
foreach ($photo in $manifest.photos) {
    if ($photo.file -ne [IO.Path]::GetFileName($photo.file)) { throw "Invalid wallpaper filename: $($photo.file)" }
    $path = Join-Path $sourceWalls $photo.file
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing wallpaper: $path" }
    if (-not $photo.artist -or -not $photo.source -or -not $photo.license_url) { throw "Missing attribution: $($photo.file)" }
    if ($photo.license -notmatch '^(CC0|Public domain|PD|CC BY(-SA)? ([1-4]\.0|2\.5))$') { throw "Unapproved or missing license: $($photo.file)" }
    if (-not $credits.Contains($photo.file) -or -not $credits.Contains($photo.source) -or -not $credits.Contains($photo.license_url)) { throw "Missing credit row: $($photo.file)" }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $photo.sha256) { throw "Wallpaper checksum mismatch: $($photo.file)" }
    $image = [Drawing.Image]::FromFile($path)
    try {
        if ($image.Width -lt 3840 -or $image.Height -lt 2160 -or $image.Width -ne $photo.width -or $image.Height -ne $photo.height) {
            throw "Wallpaper dimensions do not meet the native 4K policy: $($photo.file)"
        }
    } finally { $image.Dispose() }
}
foreach ($name in @($manifest.default_wallpaper, $manifest.lock_screen)) {
    if ($name -notin @($manifest.photos.file)) { throw "Default image is not in the curated collection: $name" }
}
if ($ValidateOnly) {
    Write-Host "Validated $($files.Count) native 4K wallpapers and their manifest. No files or settings changed."
    return
}

$Themes = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Themes'
$Root = Join-Path $Themes 'CozyAutumn'
$Walls = Join-Path $Root 'Wallpapers'
$Snd = Join-Path $Root 'Sounds'
$Cur = Join-Path $Root 'Cursors'
$SchemeKey = 'CozyAutumn'
$SchemeName = 'Cozy Autumn'
$Accent = '0XC4D9622B'   # burnt orange (AARRGGBB)

# Running from a repo clone / download: copy the assets into the Windows themes folder first.
$themeFile = Join-Path $Themes 'CozyAutumn.theme'
if ($WallpapersOnly -and -not (Test-Path -LiteralPath $themeFile)) {
    throw 'The existing CozyAutumn.theme was not found. Install the full theme first, or omit -WallpapersOnly.'
}
if ($WallpapersOnly) {
    $existingTheme = [IO.File]::ReadAllText($themeFile)
    if ($existingTheme -notmatch '(?m)^Wallpaper=' -or $existingTheme -notmatch '(?m)^ImagesRootPath=') {
        throw 'Existing theme is missing wallpaper/slideshow fields. Nothing replaced.'
    }
}
$backup = Join-Path $Root ('WallpaperBackups\' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffff'))
if ((Resolve-Path $Here).Path.TrimEnd('\') -ne $Root.TrimEnd('\')) {
    $assetFolders = if ($WallpapersOnly) { @('Wallpapers') } else { @('Wallpapers', 'Sounds', 'Cursors') }
    foreach ($d in $assetFolders) {
        if (-not (Test-Path (Join-Path $Here $d))) { throw "Missing folder next to install.ps1: $d" }
    }
    if (Test-Path -LiteralPath $Walls) {
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        robocopy $Walls (Join-Path $backup 'Wallpapers') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Backing up wallpapers failed (robocopy exit $LASTEXITCODE). Nothing replaced." }
        foreach ($name in 'wallpapers.json', 'CREDITS.md') {
            if (Test-Path -LiteralPath (Join-Path $Root $name)) { Copy-Item -LiteralPath (Join-Path $Root $name) -Destination $backup }
        }
        if (Test-Path -LiteralPath $themeFile) { Copy-Item -LiteralPath $themeFile -Destination $backup }
        Write-Host "Original collection preserved: $backup"
    }
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    foreach ($d in $assetFolders) {
        robocopy (Join-Path $Here $d) (Join-Path $Root $d) /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Copying $d failed (robocopy exit $LASTEXITCODE)" }
    }
    Copy-Item -Path (Join-Path $Here '*.ps1'), (Join-Path $Here '*.md') -Destination $Root -Force
    Copy-Item -LiteralPath $manifestPath -Destination $Root -Force
    Write-Host "Copied theme files to $Root"
}

if ($WallpapersOnly) {
    $text = $existingTheme
    $text = [regex]::Replace($text, '(?m)^Wallpaper=[^\r\n]*', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) "Wallpaper=$(Join-Path $Walls $manifest.default_wallpaper)" })
    $text = [regex]::Replace($text, '(?m)^ImagesRootPath=[^\r\n]*', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) "ImagesRootPath=$Walls" })
    [IO.File]::WriteAllText($themeFile, $text, [Text.UnicodeEncoding]::new($false, $true))
    if ($Apply) {
        Start-Process "$env:SystemRoot\system32\rundll32.exe" -ArgumentList "`"$env:SystemRoot\system32\themecpl.dll`",OpenThemeAction `"$themeFile`""
    }
    if ($LockScreen) { & (Join-Path $Root 'set-lockscreen.ps1') -Image (Join-Path $Walls $manifest.lock_screen) }
    Write-Host "Updated wallpapers only: $($files.Count). Sounds, cursors and theme colors preserved."
    return
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
$first = Get-Item -LiteralPath (Join-Path $Walls $manifest.default_wallpaper)
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

$text = $sb.ToString()
# Plain ASCII like the built-in themes; fall back to UTF-16 (also supported) if a path has non-ASCII characters.
$enc = if ($text -match '[^\x00-\x7F]') { [System.Text.UnicodeEncoding]::new($false, $true) } else { [System.Text.Encoding]::ASCII }
[System.IO.File]::WriteAllText($themeFile, $text, $enc)
Remove-Item -LiteralPath (Join-Path $Themes 'Cozy Autumn.theme') -Force -ErrorAction SilentlyContinue
Write-Host "Theme written: $themeFile"
Write-Host "Wallpapers: $((Get-ChildItem $Walls -Filter *.jpg).Count)"

if ($Apply) {
    Start-Process "$env:SystemRoot\system32\rundll32.exe" -ArgumentList "`"$env:SystemRoot\system32\themecpl.dll`",OpenThemeAction `"$themeFile`""
    Write-Host 'Applying theme...'
}

if ($LockScreen) {
    & (Join-Path $Root 'set-lockscreen.ps1') -Image (Join-Path $Walls $manifest.lock_screen)
}
