#!/usr/bin/env python3
"""
Paste to Explorer
Screenshot -> Ctrl+V in Explorer -> Save as file.
Supports: multiple images, mixed image+text, video files.
"""

import os, sys, json, time, queue, threading, ctypes, shutil, struct
from ctypes import wintypes
from datetime import datetime
from io import BytesIO
from pathlib import Path

try:
    import pystray
    from pystray import MenuItem as TrayItem, Icon as TrayIcon
except ImportError:
    print("Missing pystray. Run: pip install pystray"); sys.exit(1)

try:
    from PIL import Image, ImageGrab
except ImportError:
    print("Missing Pillow. Run: pip install Pillow"); sys.exit(1)

try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("Missing customtkinter. Run: pip install customtkinter"); sys.exit(1)

try:
    import win32gui, win32con, win32api, win32com.client, pythoncom
    import win32clipboard, win32event
except ImportError:
    print("Missing pywin32. Run: pip install pywin32"); sys.exit(1)

# ── Win32 API ─────────────────────────────
user32 = ctypes.windll.user32
user32.SetWindowsHookExW.argtypes = [wintypes.INT, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HANDLE
user32.CallNextHookEx.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

WH_KEYBOARD_LL = 13; WM_KEYDOWN = 0x0100

VK_CODES = {c: ord(c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'}
VK_MOD_MAP = {
    'ctrl': (0xA2, 0xA3), 'shift': (0xA0, 0xA1),
    'alt': (0xA4, 0xA5), 'win': (0x5B, 0x5C),
}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

# ── Path & Config ─────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = Path(os.path.dirname(sys.executable))
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', str(APP_DIR)))
    CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / "PasteToExplorer"
    ASSETS_DIR = BUNDLE_DIR / "assets"
else:
    APP_DIR = Path(__file__).parent.resolve()
    BUNDLE_DIR = APP_DIR
    CONFIG_DIR = APP_DIR
    ASSETS_DIR = APP_DIR / "assets"

CONFIG_PATH = CONFIG_DIR / "config.json"
LOGO_PATH = ASSETS_DIR / "images" / "logo.png"
LOGO0_PATH = ASSETS_DIR / "images" / "logo0.png"
TRAY_PATH = BUNDLE_DIR / "tray_icon.png"

DEFAULT_CONFIG = {
    "language": "auto",
    "hotkey_key": "V", "hotkey_modifiers": ["ctrl"],
    "filename_prefix": "Screenshot",
    "filename_rule": "timestamp",
    "image_format": "png", "jpg_quality": 90,
    "save_video": False, "save_text": False,
    "show_notification": True,
}

# ── i18n ──────────────────────────────────
T = {
    "en": {
        "win_title": "Paste to Explorer",
        "status": "Status", "settings": "Settings", "about": "About",
        "running": "Running",
        "welcome_title": "Welcome back",
        "welcome_sub": "Hook active — ready to paste images into Explorer",
        "active_badge": "Active",
        "total_saved": "Total Saved",
        "session_saved": "This Session",
        "uptime": "Uptime",
        "recent_save": "Recent Save",
        "no_saves_yet": "No saves yet",
        "settings_title": "Settings",
        "settings_sub": "Customize behavior and appearance",
        "sec_lang_hotkey": "Language && Hotkey",
        "sec_file_naming": "File Naming",
        "sec_image": "Image Settings",
        "sec_features": "Features",
        "language": "Language", "hotkey": "Hotkey",
        "filename_prefix": "Filename Prefix", "filename_rule": "Filename Rule",
        "rule_timestamp": "Timestamp: prefix_20260521_143022",
        "rule_datetime": "Date+Time: prefix_2026-05-21_14-30-22",
        "rule_date_seq": "Date+Seq: prefix_2026-05-21_001",
        "rule_sequential": "Sequential: prefix_001, prefix_002...",
        "image_format": "Image Format", "jpg_quality": "JPG Quality",
        "save_video": "Save video files from clipboard",
        "save_text": "Save text as .txt",
        "notifications": "Show notifications after save",
        "apply": "Apply Changes", "reset": "Reset Defaults",
        "applied": "Settings saved",
        "applied_msg": "Your changes have been saved.",
        "lang_changed": "Language updated. The window will refresh.",
        "about_desc": "Screenshot → Ctrl+V in Explorer → Save as file",
        "about_support": "Support us if you like this tool",
        "support_us": "Support Us",
        "qr_missing": "Place a QR code as assets/zanshang.png\nor zanshang.png in the install folder",
        "version": "Version", "exit": "Exit", "show_window": "Show Window",
        "cfg_prefix": "Screenshot",
        "notify_saved": "Saved", "notify_saved_d": "{}",
        "notify_fail": "Save failed", "notify_fail_d": "Cannot get Explorer path",
        "notify_no_img": "No image in clipboard",
        "notify_no_img_d": "Take a screenshot or copy images first",
        "notify_no_exp": "Explorer not detected",
        "notify_no_exp_d": "Open a folder window first",
    },
    "zh": {
        "win_title": "Paste to Explorer",
        "status": "状态", "settings": "设置", "about": "关于",
        "running": "运行中",
        "welcome_title": "欢迎使用",
        "welcome_sub": "钩子已激活 — 准备好向资源管理器粘贴图片",
        "active_badge": "运行中",
        "total_saved": "累计保存",
        "session_saved": "本次会话",
        "uptime": "运行时长",
        "recent_save": "最近保存",
        "no_saves_yet": "暂无记录",
        "settings_title": "设置",
        "settings_sub": "自定义行为和外观",
        "sec_lang_hotkey": "语言与快捷键",
        "sec_file_naming": "文件命名",
        "sec_image": "图片设置",
        "sec_features": "功能选项",
        "language": "界面语言", "hotkey": "快捷键",
        "filename_prefix": "文件名前缀", "filename_rule": "文件命名规则",
        "rule_timestamp": "时间戳：截图_20260521_143022",
        "rule_datetime": "日期时间：截图_2026-05-21_14-30-22",
        "rule_date_seq": "日期+序号：截图_2026-05-21_001",
        "rule_sequential": "递增序号：截图_001, 截图_002...",
        "image_format": "图片格式", "jpg_quality": "JPG 质量",
        "save_video": "保存剪贴板中的视频文件",
        "save_text": "将文本保存为 .txt 文件",
        "notifications": "保存后显示通知",
        "apply": "应用更改", "reset": "重置为默认",
        "applied": "设置已保存",
        "applied_msg": "你的设置已保存。",
        "lang_changed": "语言已更新，窗口将自动刷新。",
        "about_desc": "截图 → 资源管理器中 Ctrl+V → 存为文件",
        "about_support": "如果你喜欢这个工具，欢迎支持我们",
        "support_us": "支持我们",
        "qr_missing": "请把赞赏码命名为 assets/zanshang.png\n或者放到安装目录的 zanshang.png",
        "version": "版本", "exit": "退出", "show_window": "显示窗口",
        "cfg_prefix": "截图",
        "notify_saved": "已保存", "notify_saved_d": "{}",
        "notify_fail": "保存失败", "notify_fail_d": "无法获取资源管理器路径",
        "notify_no_img": "剪贴板中无图片",
        "notify_no_img_d": "请先截图或复制图片",
        "notify_no_exp": "未检测到资源管理器",
        "notify_no_exp_d": "请先打开文件夹窗口",
    }
}

def detect_language():
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "zh" if (lid & 0x3FF) == 0x04 else "en"
    except: return "en"

def get_explorer_path(hwnd_override=None):
    fg = hwnd_override or win32gui.GetForegroundWindow()
    if not fg: return None
    cls = win32gui.GetClassName(fg)
    if cls not in ("CabinetWClass", "ExploreWClass", "WorkerW"): return None
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        for w in shell.Windows():
            try:
                if int(w.HWND) == fg:
                    folder = w.Document.Folder
                    if folder:
                        p = folder.Self.Path
                        if p and os.path.isdir(p): return p
            except: pass
    finally: pythoncom.CoUninitialize()
    return None


class App:
    def __init__(self):
        self.config = self._load_config()
        lc = self.config.get("language", "auto")
        self.lang = detect_language() if lc == "auto" else (lc if lc in ("en","zh") else "en")
        if "filename_prefix" not in self.config:
            self.config["filename_prefix"] = self._t("cfg_prefix")
        self._running = False
        self._hook_id = None; self._tray = None
        self._last_path = None; self._total_count = 0
        self._session_count = 0; self._start_time = datetime.now()
        self._save_queue = queue.Queue(maxsize=32)
        self._win = None

    def _t(self, k): return T.get(self.lang, T["en"]).get(k, k)

    def _load_config(self):
        cfg = dict(DEFAULT_CONFIG)
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f: cfg.update(json.load(f))
            except: pass
        else:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg

    def _save_config(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f: json.dump(self.config, f, ensure_ascii=False, indent=2)
        except: pass

    def _gen_path(self, out_dir, ext=None, batch_seq=None):
        pre = self.config.get("filename_prefix", "Screenshot")
        fmt = ext or self.config["image_format"]
        now = datetime.now(); rule = self.config.get("filename_rule", "timestamp")
        seq = self.config.get("_seq", 1)
        ts = now.strftime('%Y%m%d_%H%M%S'); ds = now.strftime('%Y-%m-%d')
        dt = now.strftime('%Y-%m-%d_%H-%M-%S')
        if rule == "timestamp":
            ms = now.strftime('%f')[:3]
            base = f"{pre}_{ts}_{ms}"
            name = f"{base}{'_' + str(batch_seq).zfill(2) if batch_seq else ''}.{fmt}"
        elif rule == "datetime":
            name = f"{pre}_{dt}{'_' + str(batch_seq).zfill(2) if batch_seq else ''}.{fmt}"
        elif rule == "date_seq":
            name = f"{pre}_{ds}_{str(seq).zfill(3)}{'.' + str(batch_seq).zfill(2) if batch_seq else ''}.{fmt}"
            self.config["_seq"] = seq + 1
        elif rule == "sequential":
            name = f"{pre}_{str(seq).zfill(3)}.{fmt}"
            self.config["_seq"] = seq + 1
        else:
            name = f"{pre}_{ts}.{fmt}"
        return os.path.join(out_dir, name)

    def _dib_to_pil(self, dib):
        try:
            header_size = struct.unpack("<I", dib[:4])[0]
            bpp = struct.unpack("<H", dib[14:16])[0]
            compression = struct.unpack("<I", dib[16:20])[0]
            palette_bytes = 4 * (2 ** bpp) if bpp <= 8 else 0
            if compression == 3 and palette_bytes == 0:
                palette_bytes = 12
            offset = 14 + header_size + palette_bytes
            file_size = 14 + len(dib)
            bmp_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, offset)
            return Image.open(BytesIO(bmp_header + dib))
        except Exception as e:
            print(f"[clipboard] DIB->PIL failed: {e}")
            return None

    def _get_images(self):
        imgs = []
        try:
            r = ImageGrab.grabclipboard()
            if r is not None:
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, str) and os.path.isfile(item):
                            ext = os.path.splitext(item)[1].lower()
                            if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff'}:
                                try: imgs.append(Image.open(item).copy())
                                except Exception as e: print(f"[clipboard] open {item} failed: {e}")
                        elif hasattr(item, 'save'):
                            imgs.append(item)
                elif hasattr(r, 'save'):
                    imgs.append(r)
        except Exception as e:
            print(f"[clipboard] PIL grabclipboard failed: {e}")

        if imgs: return imgs

        try:
            win32clipboard.OpenClipboard()
            try:
                try:
                    cf_png = win32clipboard.RegisterClipboardFormat("PNG")
                    if win32clipboard.IsClipboardFormatAvailable(cf_png):
                        data = win32clipboard.GetClipboardData(cf_png)
                        if data:
                            imgs.append(Image.open(BytesIO(data)).copy())
                except Exception as e:
                    print(f"[clipboard] PNG format read failed: {e}")
                if not imgs:
                    try:
                        cf_jpeg = win32clipboard.RegisterClipboardFormat("JFIF")
                        if win32clipboard.IsClipboardFormatAvailable(cf_jpeg):
                            data = win32clipboard.GetClipboardData(cf_jpeg)
                            if data:
                                imgs.append(Image.open(BytesIO(data)).copy())
                    except Exception:
                        pass
                if not imgs and win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIBV5):
                    try:
                        data = win32clipboard.GetClipboardData(win32con.CF_DIBV5)
                        if data:
                            im = self._dib_to_pil(data)
                            if im is not None: imgs.append(im)
                    except Exception as e:
                        print(f"[clipboard] CF_DIBV5 read failed: {e}")
                if not imgs and win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    try:
                        data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                        if data:
                            im = self._dib_to_pil(data)
                            if im is not None: imgs.append(im)
                    except Exception as e:
                        print(f"[clipboard] CF_DIB read failed: {e}")
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[clipboard] win32 fallback failed: {e}")

        return imgs

    def _get_text_win32(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            finally: win32clipboard.CloseClipboard()
        except: pass
        return None

    def _get_files_win32(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    if isinstance(data, (tuple, list)):
                        return list(data)
            finally: win32clipboard.CloseClipboard()
        except: pass
        return []

    def _query_clipboard(self):
        images = self._get_images()
        text = self._get_text_win32() if self.config.get("save_text", False) else None
        video_files = []; has_plain = False
        if self.config.get("save_video", False) or not images:
            for f in self._get_files_win32():
                if os.path.splitext(f)[1].lower() in VIDEO_EXTS and self.config.get("save_video", False):
                    video_files.append(f)
                elif not images and text is None:
                    has_plain = True
        return images, text, video_files, has_plain

    def _save_img(self, img, out_dir, batch_seq=None):
        try:
            fmt = self.config["image_format"]
            fp = self._gen_path(out_dir, batch_seq=batch_seq)
            si = img.convert("RGB") if fmt == "jpg" else img
            kw = {"quality": self.config.get("jpg_quality", 90)} if fmt == "jpg" else {}
            os.makedirs(out_dir, exist_ok=True)
            si.save(fp, format=fmt.upper(), **kw)
            return True, fp
        except Exception as e: return False, str(e)

    def _save_text(self, text, out_dir, batch_seq=None):
        try:
            fp = self._gen_path(out_dir, ext="txt", batch_seq=batch_seq)
            os.makedirs(out_dir, exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f: f.write(text)
            return True, fp
        except Exception as e: return False, str(e)

    def _copy_file(self, src, out_dir, batch_seq=None):
        try:
            name = os.path.basename(src)
            dst = os.path.join(out_dir, name)
            if os.path.exists(dst) and batch_seq:
                root, ext = os.path.splitext(name)
                dst = os.path.join(out_dir, f"{root}_{str(batch_seq).zfill(2)}{ext}")
            shutil.copy2(src, dst)
            return True, dst
        except Exception as e: return False, str(e)

    def _notify(self, title, msg):
        try:
            if self._tray: self._tray.notify(msg, title)
        except: pass

    def _handle_save(self, hwnd, images, text, video_files):
        if win32gui.GetForegroundWindow() != hwnd: return
        path = get_explorer_path(hwnd)
        if not path: return
        if not images and text is None and not video_files: return
        saved = 0; total = len(images) + (1 if text else 0) + len(video_files); bs = 0
        for img in images:
            bs += 1; ok, r = self._save_img(img, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        if text:
            bs += 1; ok, r = self._save_text(text, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        for vf in video_files:
            bs += 1; ok, r = self._copy_file(vf, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        self._total_count += saved; self._session_count += saved
        if self._win: self._win.update_status()
        if saved > 0 and self.config.get("show_notification", True):
            msg = f"{saved} file(s)" if saved > 1 else os.path.basename(self._last_path or "")
            self._notify(self._t("notify_saved"), self._t("notify_saved_d").format(msg))

    HOOKPROC = ctypes.CFUNCTYPE(wintypes.LPARAM, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
    def _hook_proc(self, nc, wp, lp):
        if nc >= 0 and wp == WM_KEYDOWN:
            kbd = ctypes.cast(lp, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            target = self.config.get("hotkey_key", "V").upper()
            vk = VK_CODES.get(target, 0x56)
            if kbd.vkCode == vk:
                mods = self.config.get("hotkey_modifiers", ["ctrl"])
                ok = True
                for m, (lc, rc) in VK_MOD_MAP.items():
                    p = (user32.GetAsyncKeyState(lc) & 0x8000) or (user32.GetAsyncKeyState(rc) & 0x8000)
                    if m in mods and not p: ok = False
                    elif m not in mods and p: ok = False
                if ok and self._test_and_queue(): return 1
        return user32.CallNextHookEx(self._hook_id, nc, wp, lp)

    def _test_and_queue(self):
        fg = win32gui.GetForegroundWindow()
        if not fg: return False
        if win32gui.GetClassName(fg) not in ("CabinetWClass", "ExploreWClass"): return False
        # Read all clipboard data ONCE, pass it through queue
        images, text, video_files, has_plain = self._query_clipboard()
        if not images and text is None and not video_files: return False
        try:
            self._save_queue.put_nowait((fg, images, text, video_files))
            return True
        except queue.Full: return True

    def _run_hook(self):
        proc = self.HOOKPROC(self._hook_proc)
        self._hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, proc, None, 0)
        if not self._hook_id: return
        msg = wintypes.MSG()
        while self._running:
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0: break
        if self._hook_id: user32.UnhookWindowsHookEx(self._hook_id); self._hook_id = None

    def _save_worker(self):
        while self._running:
            try:
                item = self._save_queue.get(timeout=0.5)
                if item and len(item) == 4:
                    self._handle_save(*item)
            except (queue.Empty, TypeError, ValueError): continue

    def _tray_image(self):
        if TRAY_PATH.exists():
            try: return Image.open(TRAY_PATH)
            except: pass
        if LOGO0_PATH.exists():
            try: return Image.open(LOGO0_PATH).resize((64, 64), Image.LANCZOS)
            except: pass
        # Fallback: solid color
        return Image.new("RGBA", (64, 64), (0, 120, 215))

    def _run_tray(self):
        self._tray = TrayIcon(
            "pte", self._tray_image(), "Paste to Explorer",
            pystray.Menu(
                TrayItem(self._t("show_window"), lambda: self._win and self._win.show(), default=True),
                pystray.Menu.SEPARATOR,
                TrayItem(self._t("exit"), lambda: self._stop()),
            )
        )
        self._tray.run()

    def _stop(self):
        self._running = False
        if self._tray: self._tray.stop()
        if self._win:
            try: self._win.destroy()
            except: pass

    def save_now(self):
        path = get_explorer_path()
        if not path:
            self._notify(self._t("notify_no_exp"), self._t("notify_no_exp_d")); return
        images, text, video_files, _ = self._query_clipboard()
        if not images and text is None and not video_files:
            self._notify(self._t("notify_no_img"), self._t("notify_no_img_d")); return
        saved = 0; total = len(images) + (1 if text else 0) + len(video_files); bs = 0
        for img in images:
            bs += 1; ok, r = self._save_img(img, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        if text:
            bs += 1; ok, r = self._save_text(text, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        for vf in video_files:
            bs += 1; ok, r = self._copy_file(vf, path, batch_seq=(bs if total > 1 else None))
            if ok: saved += 1; self._last_path = r
        self._total_count += saved; self._session_count += saved
        if self._win: self._win.update_status()
        msg = f"{saved} file(s)" if saved > 1 else os.path.basename(self._last_path or "")
        self._notify(self._t("notify_saved"), self._t("notify_saved_d").format(msg))

    def run(self):
        self._running = True
        # Create named mutex for installer upgrade detection (keep handle to prevent GC)
        try:
            self._mutex = win32event.CreateMutex(None, False, "PasteToExplorer")
        except Exception:
            self._mutex = None
        threading.Thread(target=self._run_hook, daemon=True).start()
        threading.Thread(target=self._save_worker, daemon=True).start()
        time.sleep(0.3)
        threading.Thread(target=self._run_tray, daemon=True).start()
        time.sleep(0.3)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._win = GUIWindow(self)
        self._win.mainloop()


class GUIWindow(ctk.CTk):
    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    ACCENT_LIGHT = "#60a5fa"
    SUCCESS = "#22c55e"
    BG_DARK = "#0f172a"
    BG_CARD = "#1e293b"
    BG_CARD_HOVER = "#334155"
    BG_SIDEBAR = "#0f1729"
    TEXT_MAIN = "#f1f5f9"
    TEXT_MUTED = "#94a3b8"
    TEXT_DIM = "#64748b"
    BORDER = "#334155"

    def __init__(self, app):
        super().__init__()
        self.withdraw()
        self.app = app
        self.title(app._t("win_title"))
        self.geometry("880x620")
        self.minsize(800, 560)
        self.configure(fg_color=self.BG_DARK)

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"880x620+{(sw-880)//2}+{(sh-620)//2}")

        try:
            if LOGO0_PATH.exists():
                i = Image.open(LOGO0_PATH).resize((64, 64), Image.LANCZOS)
                self.iconphoto(False, ctk.CTkImage(i, size=(64, 64)))
        except Exception:
            pass

        self._current_page = None
        self._build_layout()
        self._show_page("status")

        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Control-w>", lambda e: self.hide())
        self.bind("<Escape>", lambda e: self.hide())

    def show(self):
        self.update_status()
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

    def hide(self):
        self.withdraw()

    def _rebuild_ui(self):
        for child in self.winfo_children():
            child.destroy()
        self.title(self.app._t("win_title"))
        prev_page = self._current_page or "status"
        self._current_page = None
        self._build_layout()
        self._show_page(prev_page)

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._content = ctk.CTkFrame(self, fg_color=self.BG_DARK, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        s = ctk.CTkFrame(self, fg_color=self.BG_SIDEBAR, corner_radius=0, width=220)
        s.grid(row=0, column=0, sticky="nsew")
        s.grid_propagate(False)

        hdr = ctk.CTkFrame(s, fg_color="transparent", height=110)
        hdr.pack(fill="x", padx=20, pady=(24, 8))
        hdr.pack_propagate(False)

        try:
            if LOGO0_PATH.exists():
                logo = Image.open(LOGO0_PATH).resize((52, 52), Image.LANCZOS)
                ctk.CTkLabel(hdr, text="", image=ctk.CTkImage(logo, size=(52, 52))).pack(pady=(6, 4))
        except Exception:
            pass
        ctk.CTkLabel(hdr, text="Paste to Explorer",
                     font=("Segoe UI", 13, "bold"),
                     text_color=self.TEXT_MAIN).pack()

        ctk.CTkFrame(s, height=1, fg_color=self.BORDER).pack(fill="x", padx=20, pady=(10, 18))

        self._nav_buttons = {}
        for key, icon in [
            ("status",   "\u25c9"),
            ("settings", "\u2699"),
            ("about",    "\u2665"),
        ]:
            label = self.app._t(key)
            b = ctk.CTkButton(
                s, text=f"  {icon}   {label}",
                font=("Segoe UI", 13),
                anchor="w", height=44, corner_radius=10,
                fg_color="transparent",
                hover_color=self.BG_CARD_HOVER,
                text_color=self.TEXT_MUTED,
                command=lambda k=key: self._show_page(k),
            )
            b.pack(fill="x", padx=12, pady=3)
            self._nav_buttons[key] = b

        ftr = ctk.CTkFrame(s, fg_color="transparent")
        ftr.pack(side="bottom", fill="x", padx=20, pady=20)
        ctk.CTkLabel(ftr, text="v1.0.0",
                     font=("Segoe UI", 10),
                     text_color=self.TEXT_DIM).pack(anchor="w")
        ctk.CTkLabel(ftr, text="\u00a9 2026",
                     font=("Segoe UI", 10),
                     text_color=self.TEXT_DIM).pack(anchor="w")

    def _show_page(self, key):
        if self._current_page == key:
            return
        for c in self._content.winfo_children():
            c.destroy()
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=self.ACCENT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=self.TEXT_MUTED)
        builder = getattr(self, f"_page_{key}", None)
        if builder:
            builder()
        self._current_page = key

    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=self.BG_CARD,
                            corner_radius=14, border_width=1,
                            border_color=self.BORDER, **kw)

    def _h1(self, parent, text):
        return ctk.CTkLabel(parent, text=text,
                            font=("Segoe UI", 24, "bold"),
                            text_color=self.TEXT_MAIN, anchor="w")

    def _h2(self, parent, text):
        return ctk.CTkLabel(parent, text=text,
                            font=("Segoe UI", 14, "bold"),
                            text_color=self.TEXT_MAIN, anchor="w")

    def _muted(self, parent, text):
        return ctk.CTkLabel(parent, text=text,
                            font=("Segoe UI", 11),
                            text_color=self.TEXT_MUTED, anchor="w")

    def _page_status(self):
        t = self.app._t
        wrap = ctk.CTkScrollableFrame(self._content, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)

        hero = self._card(wrap)
        hero.pack(fill="x", pady=(0, 18))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=22)
        self._h1(inner, t("welcome_title")).pack(anchor="w")
        sub = ctk.CTkFrame(inner, fg_color="transparent")
        sub.pack(anchor="w", pady=(6, 0))
        self._muted(sub, t("welcome_sub")).pack(side="left")
        badge = ctk.CTkFrame(inner, fg_color="#14532d", corner_radius=20, height=28)
        badge.pack(anchor="w", pady=(12, 0))
        ctk.CTkLabel(badge, text=f"  \u25cf  {t('active_badge')}  ",
                     font=("Segoe UI", 11, "bold"),
                     text_color=self.SUCCESS).pack(padx=6, pady=2)

        sg = ctk.CTkFrame(wrap, fg_color="transparent")
        sg.pack(fill="x", pady=(0, 18))
        sg.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self._stat_widgets = {}
        for col, (key, icon, color) in enumerate([
            ("total",   "\u25b2", self.ACCENT_LIGHT),
            ("session", "\u25c6", "#a78bfa"),
            ("uptime",  "\u23f1", "#fbbf24"),
        ]):
            c = self._card(sg)
            c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 8 if col < 2 else 0))
            ic = ctk.CTkLabel(c, text=icon, font=("Segoe UI", 22), text_color=color)
            ic.pack(anchor="w", padx=18, pady=(16, 0))
            val = ctk.CTkLabel(c, text="0", font=("Segoe UI", 28, "bold"),
                               text_color=self.TEXT_MAIN, anchor="w")
            val.pack(anchor="w", padx=18, pady=(2, 0))
            label_key = "total_saved" if key == "total" else ("session_saved" if key == "session" else "uptime")
            lbl = ctk.CTkLabel(c, text=t(label_key), font=("Segoe UI", 11),
                               text_color=self.TEXT_MUTED, anchor="w")
            lbl.pack(anchor="w", padx=18, pady=(0, 16))
            self._stat_widgets[key] = val

        ls = self._card(wrap)
        ls.pack(fill="x", pady=(0, 0))
        li = ctk.CTkFrame(ls, fg_color="transparent")
        li.pack(fill="x", padx=22, pady=18)
        rowh = ctk.CTkFrame(li, fg_color="transparent")
        rowh.pack(fill="x")
        ctk.CTkLabel(rowh, text="\u2630", font=("Segoe UI", 16),
                     text_color=self.ACCENT_LIGHT).pack(side="left", padx=(0, 10))
        self._h2(rowh, t("recent_save")).pack(side="left")
        self._sfile = ctk.CTkLabel(li, text="\u2014",
                                    font=("Segoe UI Semibold", 13),
                                    text_color=self.TEXT_MAIN, anchor="w")
        self._sfile.pack(anchor="w", pady=(10, 2))
        self._spath = ctk.CTkLabel(li, text=t("no_saves_yet"),
                                    font=("Segoe UI", 10),
                                    text_color=self.TEXT_DIM, anchor="w")
        self._spath.pack(anchor="w")

        self.update_status()

    def update_status(self):
        if not hasattr(self, "_stat_widgets"):
            return
        a = self.app
        try:
            self._stat_widgets["total"].configure(text=str(a._total_count))
            self._stat_widgets["session"].configure(text=str(a._session_count))
            e = datetime.now() - a._start_time
            h, rem = divmod(int(e.total_seconds()), 3600)
            m, _ = divmod(rem, 60)
            self._stat_widgets["uptime"].configure(text=f"{h}h {m:02d}m")
            if a._last_path:
                self._sfile.configure(text=os.path.basename(a._last_path))
                self._spath.configure(text=os.path.dirname(a._last_path))
            else:
                self._sfile.configure(text="\u2014")
                self._spath.configure(text=a._t("no_saves_yet"))
        except Exception:
            pass

    def _section(self, parent, icon, title):
        c = self._card(parent)
        c.pack(fill="x", pady=(0, 14))
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(18, 0))
        ctk.CTkLabel(head, text=icon, font=("Segoe UI", 18),
                     text_color=self.ACCENT_LIGHT).pack(side="left", padx=(0, 10))
        self._h2(head, title).pack(side="left")
        ctk.CTkFrame(c, height=1, fg_color=self.BORDER).pack(fill="x", padx=22, pady=(12, 8))
        body = ctk.CTkFrame(c, fg_color="transparent")
        body.pack(fill="x", padx=22, pady=(4, 20))
        return body

    def _formrow(self, parent, label):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", pady=6)
        ctk.CTkLabel(r, text=label, width=130, anchor="w",
                     font=("Segoe UI", 12),
                     text_color=self.TEXT_MUTED).pack(side="left")
        return r

    def _page_settings(self):
        t = self.app._t
        wrap = ctk.CTkScrollableFrame(self._content, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)

        self._h1(wrap, t("settings_title")).pack(anchor="w", pady=(0, 4))
        self._muted(wrap, t("settings_sub")).pack(anchor="w", pady=(0, 18))

        s1 = self._section(wrap, "\u2630", t("sec_lang_hotkey"))
        r = self._formrow(s1, t("language"))
        self._lv = ctk.StringVar(value=self.app.lang)
        ctk.CTkOptionMenu(r, values=["auto", "en", "zh"], variable=self._lv,
                          width=140, height=34, corner_radius=8,
                          fg_color=self.BG_CARD_HOVER,
                          button_color=self.ACCENT,
                          button_hover_color=self.ACCENT_HOVER).pack(side="left")
        r = self._formrow(s1, t("hotkey"))
        self._mv = ctk.StringVar(value="+".join(self.app.config.get("hotkey_modifiers", ["ctrl"])))
        ctk.CTkOptionMenu(r, values=["ctrl", "shift", "alt", "win", "ctrl+shift", "ctrl+alt", "win+shift"],
                          variable=self._mv, width=140, height=34, corner_radius=8,
                          fg_color=self.BG_CARD_HOVER,
                          button_color=self.ACCENT,
                          button_hover_color=self.ACCENT_HOVER).pack(side="left")
        ctk.CTkLabel(r, text="  +  ", font=("Segoe UI", 12, "bold"),
                     text_color=self.TEXT_MUTED).pack(side="left")
        self._kv = ctk.StringVar(value=self.app.config.get("hotkey_key", "V"))
        ctk.CTkOptionMenu(r, values=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
                          variable=self._kv, width=70, height=34, corner_radius=8,
                          fg_color=self.BG_CARD_HOVER,
                          button_color=self.ACCENT,
                          button_hover_color=self.ACCENT_HOVER).pack(side="left")

        s2 = self._section(wrap, "\u270e", t("sec_file_naming"))
        r = self._formrow(s2, t("filename_prefix"))
        self._pv = ctk.StringVar(value=self.app.config.get("filename_prefix", "Screenshot"))
        ctk.CTkEntry(r, textvariable=self._pv, width=240, height=34, corner_radius=8,
                     fg_color=self.BG_CARD_HOVER, border_color=self.BORDER,
                     text_color=self.TEXT_MAIN).pack(side="left")
        r = self._formrow(s2, t("filename_rule"))
        self._rv = ctk.StringVar(value=self.app.config.get("filename_rule", "timestamp"))
        rfc = ctk.CTkFrame(r, fg_color="transparent")
        rfc.pack(side="left", fill="x", expand=True)
        for rn in ["timestamp", "datetime", "date_seq", "sequential"]:
            ctk.CTkRadioButton(rfc, text=t(f"rule_{rn}"),
                               variable=self._rv, value=rn,
                               font=("Segoe UI", 11),
                               text_color=self.TEXT_MAIN,
                               fg_color=self.ACCENT,
                               hover_color=self.ACCENT_HOVER).pack(anchor="w", pady=3)

        s3 = self._section(wrap, "\u25a3", t("sec_image"))
        r = self._formrow(s3, t("image_format"))
        self._fv = ctk.StringVar(value=self.app.config.get("image_format", "png"))
        ctk.CTkOptionMenu(r, values=["png", "jpg", "bmp"], variable=self._fv,
                          width=110, height=34, corner_radius=8,
                          fg_color=self.BG_CARD_HOVER,
                          button_color=self.ACCENT,
                          button_hover_color=self.ACCENT_HOVER).pack(side="left")
        r = self._formrow(s3, t("jpg_quality"))
        self._qv = ctk.IntVar(value=self.app.config.get("jpg_quality", 90))
        ctk.CTkSlider(r, from_=10, to=100, variable=self._qv, width=200,
                      button_color=self.ACCENT,
                      progress_color=self.ACCENT,
                      command=lambda v: self._ql.configure(text=str(int(v)))).pack(side="left", padx=(0, 12))
        self._ql = ctk.CTkLabel(r, text=str(self._qv.get()), width=30,
                                font=("Segoe UI", 12, "bold"),
                                text_color=self.ACCENT_LIGHT)
        self._ql.pack(side="left")

        s4 = self._section(wrap, "\u2699", t("sec_features"))
        for var, cfg_key, label in [
            ("_stv", "save_video", "save_video"),
            ("_stx", "save_text", "save_text"),
            ("_nv", "show_notification", "notifications"),
        ]:
            r = ctk.CTkFrame(s4, fg_color="transparent")
            r.pack(fill="x", pady=6)
            setattr(self, var, ctk.BooleanVar(value=self.app.config.get(cfg_key, False)))
            ctk.CTkSwitch(r, text=t(label), variable=getattr(self, var),
                          font=("Segoe UI", 12),
                          text_color=self.TEXT_MAIN,
                          progress_color=self.ACCENT,
                          button_color="white",
                          button_hover_color="#f1f5f9").pack(side="left")

        bf = ctk.CTkFrame(wrap, fg_color="transparent")
        bf.pack(fill="x", pady=(8, 20))
        ctk.CTkButton(bf, text=f"\u2713  {t('apply')}", command=self._apply,
                      font=("Segoe UI", 12, "bold"),
                      width=160, height=42, corner_radius=10,
                      fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER).pack(side="left", padx=(0, 10))
        ctk.CTkButton(bf, text=f"\u21bb  {t('reset')}", command=self._reset,
                      font=("Segoe UI", 12),
                      width=160, height=42, corner_radius=10,
                      fg_color="transparent", hover_color=self.BG_CARD,
                      border_width=1, border_color=self.BORDER,
                      text_color=self.TEXT_MAIN).pack(side="left")

    def _apply(self):
        a = self.app
        old_lang = a.lang
        a.config["language"] = self._lv.get()
        a.config["hotkey_modifiers"] = self._mv.get().split("+")
        a.config["hotkey_key"] = self._kv.get()
        a.config["filename_prefix"] = self._pv.get()
        a.config["filename_rule"] = self._rv.get()
        a.config["image_format"] = self._fv.get()
        a.config["jpg_quality"] = self._qv.get()
        a.config["save_video"] = self._stv.get()
        a.config["save_text"] = self._stx.get()
        a.config["show_notification"] = self._nv.get()
        nl = a.config["language"]
        a.lang = detect_language() if nl == "auto" else nl
        a._save_config()
        if old_lang != a.lang:
            messagebox.showinfo(a._t("applied"), a._t("lang_changed"))
            self._rebuild_ui()
        else:
            messagebox.showinfo(a._t("applied"), a._t("applied_msg"))

    def _reset(self):
        self._lv.set("auto"); self._mv.set("ctrl"); self._kv.set("V")
        self._pv.set(self.app._t("cfg_prefix")); self._rv.set("timestamp")
        self._fv.set("png"); self._qv.set(90); self._ql.configure(text="90")
        self._stv.set(False); self._stx.set(False); self._nv.set(True)

    def _page_about(self):
        t = self.app._t
        wrap = ctk.CTkScrollableFrame(self._content, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)

        hero = self._card(wrap)
        hero.pack(fill="x", pady=(0, 18))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(pady=32, padx=20)
        try:
            if LOGO_PATH.exists():
                img = Image.open(LOGO_PATH)
                w, h = img.size
                sc = min(420 / w, 110 / h, 1.0)
                nw, nh = int(w * sc), int(h * sc)
                img = img.resize((nw, nh), Image.LANCZOS)
                ctk.CTkLabel(inner, text="", image=ctk.CTkImage(img, size=(nw, nh))).pack(pady=(0, 14))
        except Exception:
            pass
        ctk.CTkLabel(inner, text="Paste to Explorer",
                     font=("Segoe UI", 26, "bold"),
                     text_color=self.TEXT_MAIN).pack()
        ctk.CTkLabel(inner, text=f"{t('version')} 1.0.0",
                     font=("Segoe UI", 11),
                     text_color=self.TEXT_DIM).pack(pady=(2, 8))
        ctk.CTkLabel(inner, text=t("about_desc"),
                     font=("Segoe UI", 12),
                     text_color=self.TEXT_MUTED).pack()

        qr_img, qr_path = self._load_qr()
        if qr_img:
            qrc = self._card(wrap)
            qrc.pack(fill="x", pady=(0, 0))
            qi = ctk.CTkFrame(qrc, fg_color="transparent")
            qi.pack(pady=24, padx=20)
            ctk.CTkLabel(qi, text=f"\u2764  {t('support_us')}",
                         font=("Segoe UI", 14, "bold"),
                         text_color="#fb7185").pack(pady=(0, 6))
            ctk.CTkLabel(qi, text=t("about_support"),
                         font=("Segoe UI", 11),
                         text_color=self.TEXT_MUTED).pack(pady=(0, 14))
            wb = ctk.CTkFrame(qi, fg_color="white", corner_radius=12)
            wb.pack(pady=(0, 8))
            ctk.CTkLabel(wb, text="", image=qr_img).pack(padx=12, pady=12)

    def _load_qr(self):
        candidates = [
            APP_DIR / "zanshang.png",
            APP_DIR / "assets" / "zanshang.png",
            APP_DIR / "assets" / "images" / "zanshang.png",
            BUNDLE_DIR / "zanshang.png",
            BUNDLE_DIR / "assets" / "zanshang.png",
            ASSETS_DIR / "zanshang.png",
            ASSETS_DIR / "images" / "zanshang.png",
        ]
        for p in candidates:
            try:
                if p.exists():
                    img = Image.open(p)
                    img.thumbnail((220, 220), Image.LANCZOS)
                    return ctk.CTkImage(img, size=img.size), str(p)
            except Exception as e:
                print(f"[QR] failed loading {p}: {e}")
                continue
        return None, None


if __name__ == "__main__":
    App().run()
