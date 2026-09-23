#Requires -Version 5.1
<# Sets the Windows lock screen to a Cozy Autumn wallpaper. Usage: .\set-lockscreen.ps1 [-Image <path>] #>
param([string]$Image = (Join-Path $PSScriptRoot 'Wallpapers\bi-501-vermont-fall-foliage.jpg'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Image)) { throw "Image not found: $Image" }
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$ext = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 }
$asOp = ($ext | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asAct = ($ext | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.System.UserProfile.LockScreen, Windows.System.UserProfile, ContentType = WindowsRuntime] | Out-Null
$t = $asOp.MakeGenericMethod([Windows.Storage.StorageFile]).Invoke($null, @([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $Image).Path)))
$t.Wait(-1) | Out-Null
$asAct.Invoke($null, @([Windows.System.UserProfile.LockScreen]::SetImageFileAsync($t.Result))).Wait(-1) | Out-Null
Write-Host "Lock screen set: $Image"
