#Requires -Version 5.1
<# Removes the Cozy Autumn theme, its sound/cursor scheme registrations and files. Switch to another theme first. #>
$ErrorActionPreference = 'SilentlyContinue'
$Themes = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Themes'
Remove-Item -LiteralPath (Join-Path $Themes 'CozyAutumn.theme') -Force
Remove-Item -LiteralPath (Join-Path $Themes 'Cozy Autumn.theme') -Force
Remove-ItemProperty -Path 'HKCU:\Control Panel\Cursors\Schemes' -Name 'Cozy Autumn', 'Cozy Autumn (large)', 'Cozy Autumn (extra large)'
Remove-Item -Path 'HKCU:\AppEvents\Schemes\Names\CozyAutumn' -Recurse -Force
Get-ChildItem 'HKCU:\AppEvents\Schemes\Apps' -Recurse | Where-Object { $_.PSChildName -eq 'CozyAutumn' } |
    ForEach-Object { Remove-Item $_.PSPath -Recurse -Force }
Remove-Item -LiteralPath (Join-Path $Themes 'CozyAutumn') -Recurse -Force
Write-Host 'Cozy Autumn removed.'
