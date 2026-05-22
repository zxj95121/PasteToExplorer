# Paste to Explorer

Screenshot → Ctrl+V in Explorer → Save as image file.

A Windows system tray utility that intercepts **Ctrl+V** in File Explorer when the clipboard contains images, and automatically saves them as files with customizable naming rules.

![status](https://img.shields.io/badge/platform-Windows%2010%20x64-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![version](https://img.shields.io/badge/version-1.0.0-blue)

## How It Works

1. **Take a screenshot** (or copy any image/text from any app — chat, browser, editor)
2. **Open File Explorer** to your target folder
3. **Press Ctrl+V** → content is automatically saved as file(s)

No need to manually save. Just paste as if pasting files.

## Features

| Feature | Description |
|---|---|
| Smart paste | Only intercepts Ctrl+V in Explorer when clipboard has saveable content. Other apps pass through. |
| Multiple images | Copy multiple images at once — each saved as a separate file. |
| Mixed content | Image + text copied together: saves both based on your settings. |
| Robust image extraction | Supports PIL clipboard, registered PNG format (chat apps), CF_DIBV5, CF_DIB, file lists. |
| Custom hotkey | Default Ctrl+V, fully configurable in Settings. |
| Naming rules | 4 presets: timestamp / date+time / date+seq / sequential. |
| Image format | PNG / JPG / BMP with configurable JPG quality. |
| Optional text save | Save clipboard text as `.txt` file. |
| Optional video save | Copy video files from clipboard. |
| Bilingual UI | Auto-detects Windows language (EN / 中文), switchable live in Settings. |
| Modern dark UI | Sidebar nav + card layout. |
| System tray | Runs silently. Right-click tray icon to configure. |

## Download

Get the latest installer from the **[Releases](https://github.com/zxj95121/PasteToExplorer/releases)** page.

Requires: **Windows 10 x64 or later**.

## Building from Source

```batch
pip install -r requirements.txt
pyinstaller clipboard_image_saver.spec
iscc installer.iss
```

Or double-click `build.bat` (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)).

### Dependencies

- Python 3.8+
- `pystray`, `Pillow`, `pywin32`, `customtkinter`, `pyinstaller`
- Inno Setup 6 (for installer)

## Configuration

Config file: `%APPDATA%\PasteToExplorer\config.json` (auto-created on first run)

```json
{
  "language": "auto",
  "hotkey_key": "V",
  "hotkey_modifiers": ["ctrl"],
  "filename_prefix": "Screenshot",
  "filename_rule": "timestamp",
  "image_format": "png",
  "jpg_quality": 90,
  "save_video": false,
  "save_text": false,
  "show_notification": true
}
```

All settings can be changed live in the in-app Settings page.

## Uninstall

Start Menu → `Paste to Explorer` → `Uninstall`, or via Windows Settings.

## License

MIT — see `LICENSE.txt`.
