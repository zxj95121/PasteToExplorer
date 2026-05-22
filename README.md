# Paste to Explorer

Screenshot → Ctrl+V in Explorer → Save as image file.

A Windows system tray utility that intercepts Ctrl+V in File Explorer when the clipboard contains images, and automatically saves them as files with customizable naming rules.

## How It Works

1. **Take a screenshot** (or copy any image/text to clipboard)
2. **Open File Explorer** to your target folder
3. **Press Ctrl+V** — the content is automatically saved as file(s)

No need to manually save images. Just paste as if pasting files.

## Features

| Feature | Description |
|---|---|
| Smart paste | Only intercepts Ctrl+V in Explorer when clipboard has images/text. Other apps pass through. |
| Multiple images | Copy multiple images at once — each saved as a separate file. |
| Mixed content | Images + text copied together: saves images (and text if enabled). |
| Text to .txt | Optional: save clipboard text as .txt files. |
| Video from clipboard | Optional: copy video files from clipboard. |
| Custom hotkey | Default Ctrl+V, fully configurable (modifiers + key). |
| Naming rules | 4 presets: timestamp, date+time, date+seq, sequential numbering. |
| Image format | PNG, JPG, BMP with configurable JPG quality. |
| Bilingual | Auto-detects Windows language (EN/ZH), switchable in Settings. |
| Notifications | Optional tray notification on each save. |
| System tray | Runs silently. Right-click tray icon to configure. |

## Download

[**Download v1.0.0 Installer**](https://github.com/zxj95121/PasteToExplorer/releases/tag/v1.0.0)

Requires: **Windows 10 x64 or later**

## Building from Source

```batch
pip install -r requirements.txt
pyinstaller clipboard_image_saver.spec
iscc installer.iss
```

Or double-click `build.bat` (requires Inno Setup 6).

### Dependencies

- Python 3.8+, pystray, Pillow, pywin32, customtkinter
- Inno Setup 6 (for installer build)

## Configuration

Config path: `%APPDATA%\PasteToExplorer\config.json` (or script directory for portable)

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

## License

MIT
