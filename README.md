# 🍁 Cozy Autumn: a Windows 11 theme

Sweater weather for your desktop. **150 native high-resolution autumn photographs** (Vermont villages, Pacific Northwest
forests, New England back roads, Stars Hollow vibes) plus a burnt-orange accent, dark mode, a
matching sound scheme and hand-drawn cursors.

![Desktop preview](docs/desktop.jpg)

## What's inside

| | |
|---|---|
| 🖼️ **Wallpapers** | 150 original JPEGs in a shuffled slideshow that changes every 30 minutes. Red/orange foliage, forests, villages, covered bridges and country roads; every selected photo was reviewed in contact sheets. |
| 🎨 **Colours** | Dark mode, burnt-orange accent `#D9622B` on the Start menu, taskbar, title bars and selection highlight |
| 🔔 **Sounds** | 20 soft, warm synthesised system sounds: logon/logoff, notifications, mail, reminders, errors, device connect, the recycle bin and more |
| 🖱️ **Cursors** | A full 17-cursor set in orange and cream, with an animated leaf spinner. Three size schemes: *Cozy Autumn*, *(Large)* and *(Extra Large)* |
| 🔒 **Lock screen** | An optional aerial autumn view of Londonderry, Vermont |

### Wallpapers

![A sample of the wallpapers](docs/wallpapers.jpg)

### Palette

![Palette](docs/palette.png)

### Cursors

![Cursors in three sizes](docs/cursors.png)

### Lock screen

![Lock screen](docs/lockscreen.jpg)

Desktop and lock-screen previews are illustrative photo previews, not screenshots of an applied
theme. Their source photos are the same defaults used by the installer and are credited in
[CREDITS.md](CREDITS.md).

### Resolution and quality

Every active wallpaper is **at least 3840 pixels wide and 2160 pixels high**; actual minimums
in this selection are 3840 wide and 2323 high. All 150 fill a 2496x1664 (3:2) display without
enlargement. Landscape ratios are between 1.3:1 and 2:1; Windows Fill may crop the edges.
Original JPEG bytes are preserved, with **no AI generation, upscaling, resizing or recompression**.
The original collection's 511 files included 221 below the primary-screen minimum and only
216 at least 3840x2160. The replacement recovers **83 existing photographs at original resolution**
and adds **67 newly selected photographs**, rather than just deleting the smaller images.

Review covered 240 downloaded candidates in eight contact sheets, plus 1:1 pixel crops from
the 30 lowest-scoring sharpness candidates. Watermarks, paintings, visibly soft frames, off-theme
subjects and visual repetition were rejected. Intentional fog, long-exposure water and selective
focus remain in a few photographs; high pixel count alone is not a guarantee of sharpness.
The native originals occupy approximately **2.3 GB**, so allow space for the installed copy and backups.

## Install

```powershell
git clone https://github.com/giulioungaretti/cozy-autumn-theme.git
cd cozy-autumn-theme
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Apply -LockScreen
```

* `install.ps1` copies the assets to `%LOCALAPPDATA%\Microsoft\Windows\Themes\CozyAutumn` and registers
  the sound and cursor schemes. It then writes `CozyAutumn.theme`.
* `-Apply` switches to the theme right away. Without it, pick **Cozy Autumn** in
  *Settings › Personalization › Themes*.
* `-LockScreen` also sets the lock screen picture. To use a different photo, run
  `.\set-lockscreen.ps1 -Image <path>`.

No admin rights are needed. Everything is per-user.

### Upgrade only the wallpapers

From this checkout, with Cozy Autumn already installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -ValidateOnly
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WallpapersOnly -Apply
```

`-ValidateOnly` checks every JPEG's dimensions, SHA-256 and manifest attribution without copying
files or changing settings. `-WallpapersOnly` replaces only the active wallpaper collection and
the `.theme` file's wallpaper/slideshow paths. Existing accent, mode, sound and cursor settings
are preserved; no Settings process is terminated. Omit `-Apply` to prepare the files without
opening the theme. `-Apply` reopens the existing theme, including its existing sound/cursor/color
definitions; it is not a snapshot of any separate personalization overrides made since that
theme was installed. Applying a theme is an explicit personalization action; these commands are
provided for you to run, not run automatically during curation.

Before replacement, the installer preserves the installed original photos, credits, manifest
(if present), and `.theme` under
`%LOCALAPPDATA%\Microsoft\Windows\Themes\CozyAutumn\WallpaperBackups\<timestamp>`.
Backups sit outside `Wallpapers`, so they are not part of the active slideshow. The personal
OneDrive copy is not used or overwritten. A full installation also backs up an existing
wallpaper collection before replacing it.

To restore, close theme settings, choose the desired backup, and run the following yourself.
This restores files but does not apply a theme or alter the lock screen:

```powershell
$root = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Themes\CozyAutumn'
$backup = Join-Path $root 'WallpaperBackups\<timestamp>'
robocopy (Join-Path $backup 'Wallpapers') (Join-Path $root 'Wallpapers') /MIR /R:1 /W:1
if ($LASTEXITCODE -ge 8) { throw "Restore failed: $LASTEXITCODE" }
Copy-Item (Join-Path $backup 'CozyAutumn.theme') (Join-Path (Split-Path $root) 'CozyAutumn.theme') -Force
foreach ($name in 'CREDITS.md', 'wallpapers.json') {
    if (Test-Path (Join-Path $backup $name)) { Copy-Item (Join-Path $backup $name) $root -Force }
}
```

The restored legacy collection may not satisfy the new validator; its missing old manifest is
not evidence of validated provenance. Keep the curated checkout to reinstall the upgraded selection.

### Tips

* **Cursor size:** change it in **Mouse Properties › Pointers** (`main.cpl`) by picking the Large or
  Extra Large scheme. Don't use the *Settings › Accessibility › Mouse pointer* size slider: it replaces
  custom cursors with the Windows defaults. If that happens, run `install.ps1 -Apply` again.
* **Double-clicking the `.theme` file does nothing?** Close Settings yourself and try opening the
  theme again. The installer does not terminate your running applications.

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

This removes the theme, the sound and cursor schemes and the installed files. Afterwards, pick any
other theme in Settings.

## How it was made

`src/` contains the tooling used to build the theme:

| Script | Purpose |
|---|---|
| `upgrade_wallpapers.py` | Audit actual JPEGs, recover source-verified Commons originals, and search Commons/Openverse without enlargement |
| `fetch_flickr_originals.py` | Search Flickr directly, verify each photographer-page license, and request its native original |
| `curate_wallpapers.py` | Generate contact sheets and pixel crops; publish the reviewed exact-byte originals, credits, manifest and previews while archiving the old worktree collection |
| `validate_wallpapers.py` | Read-only checks of all shipped images, dimensions, hashes, licenses, credits, duplicate hashes, defaults and previews |
| `fetch_wallpapers.py`, `fetch_commons2.py`, `fetch_more.py`, `fetch_bing2.py`, `fetch_bing3.py`, `finalize.py` | Historical build tooling only; uses lower size thresholds, thumbnail/recompression workflows or unverified Bing filters. Do not use it to regenerate the upgraded collection. |
| `warmth.py` | Score each image by its fraction of red/orange pixels |
| `contact.py` | Contact sheets for the manual review |
| `sounds.py` | Synthesises the 20 WAV sounds from scratch |
| `cursors.py` | Draws the cursors with supersampling and writes multi-resolution `.cur`/`.ani` files (32–256 px) in three size variants |

## Credits and licensing

* **Scripts** (`*.ps1`, `src/`) are MIT licensed. See [LICENSE](LICENSE).
* **Sounds and cursors** were generated by `src/sounds.py` and `src/cursors.py` and are also MIT.
* **Active photos** belong to their photographers. All 150 have author, source and license links in
  [CREDITS.md](CREDITS.md), with verification dates, original URLs, dimensions and SHA-256 hashes in
  [wallpapers.json](wallpapers.json). CC BY requires attribution; CC BY-SA additionally requires
  ShareAlike for derivatives. Preview derivatives retain these credits and source license terms.
* Commons live image metadata was checked for each active image; historical filename prefixes
  and the old credit table alone were not treated as proof. Searches also covered direct Flickr,
  Openverse and Public Domain Pictures. Flickr original downloads failed with rate-limit/DNS
  errors, Openverse discovery was throttled or unauthorized, and the additional download site
  was blocked; **all successfully shipped originals in this revision are hosted on Commons**.
* **Legacy uncertainty:** the previous 343 Bing files had unverified license-filter claims.
  Private visibility and personal use do not establish redistribution permission. None are in
  the improved active slideshow, but old Git history and installed backups can still contain them.
  This work does not certify the entire repository history for public redistribution.

The installed original collection was not changed during this upgrade, and no commit or push was made.
