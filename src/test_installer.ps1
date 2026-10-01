#Requires -Version 5.1
param([Parameter(Mandatory = $true)][string]$FixtureDirectory)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot
if (Test-Path -LiteralPath $FixtureDirectory) { throw 'Use a new, empty fixture directory.' }
$source = Join-Path $FixtureDirectory 'source'
$local = Join-Path $FixtureDirectory 'LocalAppData'
$themes = Join-Path $local 'Microsoft\Windows\Themes'
$root = Join-Path $themes 'CozyAutumn'
$walls = Join-Path $root 'Wallpapers'
New-Item -ItemType Directory -Path (Join-Path $source 'Wallpapers'), $walls, (Join-Path $root 'Sounds'), (Join-Path $root 'Cursors') -Force | Out-Null
foreach ($name in 'install.ps1', 'set-lockscreen.ps1', 'CREDITS.md') {
    Copy-Item -LiteralPath (Join-Path $repo $name) -Destination $source
}
$manifest = Get-Content -LiteralPath (Join-Path $repo 'wallpapers.json') -Raw | ConvertFrom-Json
$manifest.photos = @($manifest.photos | Where-Object { $_.file -in @($manifest.default_wallpaper, $manifest.lock_screen) })
foreach ($photo in $manifest.photos) {
    Copy-Item -LiteralPath (Join-Path (Join-Path $repo 'Wallpapers') $photo.file) -Destination (Join-Path $source 'Wallpapers')
}
$manifestPath = Join-Path $source 'wallpapers.json'
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Copy-Item -LiteralPath (Join-Path (Join-Path $source 'Wallpapers') $manifest.default_wallpaper) -Destination (Join-Path $walls 'legacy.jpg')
[IO.File]::WriteAllText((Join-Path $root 'Sounds\sentinel.wav'), 'Unchanged sound sentinel')
[IO.File]::WriteAllText((Join-Path $root 'Cursors\sentinel.cur'), 'Unchanged cursor sentinel')
$before = @"
[Theme]
DisplayName=Cozy Autumn
[Control Panel\Desktop]
Wallpaper=$walls\legacy.jpg
WallpaperStyle=10
[Slideshow]
ImagesRootPath=$walls
Interval=1800000
Shuffle=1
[VisualStyles]
ColorizationColor=0XC4D9622B
SystemMode=Dark
AppMode=Dark
[Control Panel\Cursors]
Arrow=$root\Cursors\sentinel.cur
[Sounds]
SchemeName=Cozy Autumn
"@
$theme = Join-Path $themes 'CozyAutumn.theme'
[IO.File]::WriteAllText($theme, $before)
$soundHash = (Get-FileHash -LiteralPath (Join-Path $root 'Sounds\sentinel.wav')).Hash
$cursorHash = (Get-FileHash -LiteralPath (Join-Path $root 'Cursors\sentinel.cur')).Hash
$legacyHash = (Get-FileHash -LiteralPath (Join-Path $walls 'legacy.jpg')).Hash
$previousLocal = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = $local
    & (Join-Path $source 'install.ps1') -ValidateOnly
    if ([IO.File]::ReadAllText($theme) -ne $before) { throw 'ValidateOnly changed the theme.' }
    $manifest.photos[0].sha256 = 'invalid'
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    $rejected = $false
    try { & (Join-Path $source 'install.ps1') -WallpapersOnly } catch {
        if ($_.Exception.Message -notlike '*checksum mismatch*') { throw }
        $rejected = $true
    }
    if (-not $rejected -or (Get-FileHash -LiteralPath (Join-Path $walls 'legacy.jpg')).Hash -ne $legacyHash) {
        throw 'Invalid manifest was not rejected before replacement.'
    }
    $fullManifest = Get-Content -LiteralPath (Join-Path $repo 'wallpapers.json') -Raw | ConvertFrom-Json
    $manifest.photos = @($fullManifest.photos | Where-Object { $_.file -in @($manifest.default_wallpaper, $manifest.lock_screen) })
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    & (Join-Path $source 'install.ps1') -WallpapersOnly
    $after = [IO.File]::ReadAllText($theme)
    $strip = { param($text) [regex]::Replace($text, '(?m)^(Wallpaper|ImagesRootPath)=[^\r\n]*', '') }
    if ((& $strip $after) -ne (& $strip $before)) { throw 'Unrelated theme settings changed.' }
    if ($after -notlike "*Wallpaper=$(Join-Path $walls $manifest.default_wallpaper)*") { throw 'Default wallpaper not updated.' }
    if ((Get-ChildItem -LiteralPath $walls -Filter *.jpg).Count -ne 2 -or (Test-Path -LiteralPath (Join-Path $walls 'legacy.jpg'))) { throw 'Legacy wallpaper leaked into the active slideshow.' }
    $backup = Get-ChildItem -LiteralPath (Join-Path $root 'WallpaperBackups') -Directory | Select-Object -First 1
    if ((Get-FileHash -LiteralPath (Join-Path $backup.FullName 'Wallpapers\legacy.jpg')).Hash -ne $legacyHash) { throw 'Legacy backup not preserved.' }
    if ([IO.File]::ReadAllText((Join-Path $backup.FullName 'CozyAutumn.theme')) -ne $before) { throw 'Original theme backup changed.' }
    if ((Get-FileHash -LiteralPath (Join-Path $root 'Sounds\sentinel.wav')).Hash -ne $soundHash -or
        (Get-FileHash -LiteralPath (Join-Path $root 'Cursors\sentinel.cur')).Hash -ne $cursorHash) { throw 'Protected assets changed.' }
    Write-Host 'PASS: read-only validation, checksum rejection, reversible replacement, no legacy slideshow files, default paths, unchanged accent/sounds/cursors. No real personalization changed.'
} finally {
    $env:LOCALAPPDATA = $previousLocal
}
