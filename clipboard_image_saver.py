#!/usr/bin/env python3
"""
Paste to Explorer
Screenshot -> Ctrl+V in Explorer -> Save as file.
Supports: multiple images, mixed image+text, video files.
"""

import os, sys, json, time, queue, threading, ctypes, shutil
from ctypes import wintypes
from datetime import datetime
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
    CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / "PasteToExplorer"
    ASSETS_DIR = APP_DIR / "assets"
else:
    APP_DIR = Path(__file__).parent.resolve()
    CONFIG_DIR = APP_DIR
    ASSETS_DIR = APP_DIR / "assets"

CONFIG_PATH = CONFIG_DIR / "config.json"
LOGO_PATH = ASSETS_DIR / "images" / "logo.png"
LOGO0_PATH = ASSETS_DIR / "images" / "logo0.png"
TRAY_PATH = APP_DIR / "tray_icon.png"

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
        "last_saved": "Last Saved", "stats": "Stats",
        "total_saved": "Total saved", "session_saved": "This session",
        "open_folder": "Open Folder", "save_now": "Save Now",
        "language": "Language", "hotkey": "Hotkey",
        "filename_prefix": "Filename Prefix", "filename_rule": "Filename Rule",
        "rule_timestamp": "Timestamp: prefix_20260521_143022",
        "rule_datetime": "Date+Time: prefix_2026-05-21_14-30-22",
        "rule_date_seq": "Date+Seq: prefix_2026-05-21_001",
        "rule_sequential": "Sequential: prefix_001, prefix_002...",
        "image_format": "Image Format", "jpg_quality": "JPG Quality",
        "save_video": "Save video files from clipboard",
        "save_text": "Save text as .txt",
        "notifications": "Show notifications",
        "apply": "Apply", "reset": "Reset",
        "applied": "Settings saved",
        "about_desc": "Screenshot -> Ctrl+V in Explorer -> Save as file",
        "about_support": "Support us if you like this tool",
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
        "last_saved": "最近保存", "stats": "统计",
        "total_saved": "累计保存" , "session_saved": "本次会话",
        "open_folder": "打开目录", "save_now": "立即保存",
        "language": "界面语言", "hotkey": "快捷键",
        "filename_prefix": "文件名前缀", "filename_rule": "文件命名规则",
        "rule_timestamp": "时间戳: 截图_20260521_143022",
        "rule_datetime": "日期时间: 截图_2026-05-21_14-30-22",
        "rule_date_seq": "日期+序号: 截图_2026-05-21_001",
        "rule_sequential": "递增序号: 截图_001, 截图_002...",
        "image_format": "图片格式", "jpg_quality": "JPG 质量",
        "save_video": "保存剪贴板视频文件",
        "save_text": "将文本保存为 .txt",
        "notifications": "保存后通知",
        "apply": "应用", "reset": "重置",
        "applied": "设置已保存",
        "about_desc": "截图 -> 资源管理器中 Ctrl+V -> 存为文件",
        "about_support": "如果喜欢这个工具，欢迎支持我们",
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

    def _get_images(self):
        try:
            r = ImageGrab.grabclipboard()
            if r is None: return []
            if isinstance(r, list): return r
            return [r]
        except: return []

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
        # Create named mutex for installer upgrade detection
        try: win32event.CreateMutex(None, False, "PasteToExplorer")
        except: pass
        threading.Thread(target=self._run_hook, daemon=True).start()
        threading.Thread(target=self._save_worker, daemon=True).start()
        time.sleep(0.3)
        threading.Thread(target=self._run_tray, daemon=True).start()
        time.sleep(0.3)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self._win = GUIWindow(self)
        self._win.protocol("WM_DELETE_WINDOW", self._win.hide)
        self._win.after(100, self._win.try_show)
        self._win.mainloop()


class GUIWindow(ctk.CTkToplevel):
    CARD_KW = dict(fg_color=("white", "gray18"), corner_radius=12)
    LABEL_KW = dict(font=("Segoe UI", 11))
    TITLE_KW = dict(font=("Segoe UI", 12, "bold"))

    def __init__(self, app):
        super().__init__()
        self.app = app; self._hidden = False
        self.title(app._t("win_title"))
        self.geometry("740x620"); self.minsize(660, 540)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"740x620+{(sw-740)//2}+{(sh-620)//2}")
        try:
            if LOGO0_PATH.exists():
                i = Image.open(LOGO0_PATH).resize((64,64), Image.LANCZOS)
                self.tk.call('wm', 'iconphoto', self._w, ctk.CTkImage(i, size=(64,64)))
        except: pass
        self.tab = ctk.CTkTabview(self, fg_color="transparent")
        self.tab.pack(fill="both", expand=True, padx=14, pady=14)
        for k in ("status","settings","about"):
            setattr(self, f"t_{k}", self.tab.add(app._t(k)))
        self._build_status(); self._build_settings(); self._build_about()
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Control-w>", lambda e: self.hide())

    def try_show(self): self.withdraw(); self._hidden = True
    def show(self):
        self._hidden = False; self.update_status()
        self.deiconify(); self.lift(); self.focus_force()
    def hide(self): self._hidden = True; self.withdraw()

    # ── helper: card wrapper ─────────────────
    def _card(self, parent, title=None):
        f = ctk.CTkFrame(parent, **self.CARD_KW)
        f.pack(fill="x", pady=(0, 12))
        if title:
            ctk.CTkLabel(f, text=title, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
            ctk.CTkFrame(f, height=1, fg_color=("#e0e0e0","#3a3a3a")).pack(fill="x", padx=16, pady=(0, 10))
        return f

    # ── Status Tab ────────────────────────────
    def _build_status(self):
        p = ctk.CTkFrame(self.t_status, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=6, pady=4)

        # Status indicator card
        sf = self._card(p)
        hf = ctk.CTkFrame(sf, fg_color="transparent")
        hf.pack(fill="x", padx=16, pady=(6, 12))
        ctk.CTkLabel(hf, text="\u25cf", font=("Segoe UI", 18), text_color="#22c55e").pack(side="left", padx=(0,6))
        self._sl = ctk.CTkLabel(hf, text=self.app._t("running"), font=("Segoe UI", 14, "bold"))
        self._sl.pack(side="left")

        # Stats cards row
        sf2 = ctk.CTkFrame(p, fg_color="transparent")
        sf2.pack(fill="x", pady=(0, 12))
        for lbl, key in [("\u2191 Total", "total"), ("\u25b6 Session", "session"), ("\u23f1 Uptime", "uptime")]:
            c = ctk.CTkFrame(sf2, **self.CARD_KW)
            c.pack(side="left", fill="x", expand=True, padx=(0, 10 if key != "uptime" else 0))
            ctk.CTkLabel(c, text=lbl, font=("Segoe UI", 11), text_color="#888888").pack(anchor="w", padx=14, pady=(12, 0))
            setattr(self, f"_s_{key}", ctk.CTkLabel(c, text="0", font=("Segoe UI", 22, "bold")))
            getattr(self, f"_s_{key}").pack(anchor="w", padx=14, pady=(0, 12))

        # Last saved card
        lf = self._card(p, "Last Saved")
        self._ll = ctk.CTkLabel(lf, text="\u2014", font=("Segoe UI", 13))
        self._ll.pack(anchor="w", padx=16, pady=(0, 4))
        self._lp = ctk.CTkLabel(lf, text="", font=("Segoe UI", 10), text_color="#888888")
        self._lp.pack(anchor="w", padx=16, pady=(0, 10))

        # Buttons
        bf = ctk.CTkFrame(p, fg_color="transparent")
        bf.pack(fill="x")
        ctk.CTkButton(bf, text=self.app._t("open_folder"), command=self._open_last,
                       width=140, height=36, fg_color="gray40").pack(side="left", padx=(0, 10))
        ctk.CTkButton(bf, text=self.app._t("save_now"), command=self.app.save_now,
                       width=160, height=36, fg_color="#2563eb", hover_color="#1d4ed8").pack(side="left")

        self.update_status()

    def update_status(self):
        a = self.app
        self._ll.configure(text=os.path.basename(a._last_path) if a._last_path else "\u2014")
        self._lp.configure(text=os.path.dirname(a._last_path) if a._last_path else "")
        e = datetime.now() - a._start_time
        h, rem = divmod(int(e.total_seconds()), 3600); m, s = divmod(rem, 60)
        self._s_total.configure(text=str(a._total_count))
        self._s_session.configure(text=str(a._session_count))
        self._s_uptime.configure(text=f"{h}h {m:02d}m")

    def _open_last(self):
        if self.app._last_path and os.path.exists(self.app._last_path):
            os.startfile(os.path.dirname(self.app._last_path))

    # ── Settings Tab ──────────────────────────
    def _setting_card(self, parent, title):
        f = ctk.CTkFrame(parent, **self.CARD_KW)
        f.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkFrame(f, height=1, fg_color=("#e0e0e0","#3a3a3a")).pack(fill="x", padx=16, pady=(0, 10))
        return f

    def _row(self, parent):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=4)
        return r

    def _build_settings(self):
        f = ctk.CTkScrollableFrame(self.t_settings)
        f.pack(fill="both", expand=True, padx=6, pady=4)

        # ── Language & Hotkey ──
        c1 = self._setting_card(f, "Language && Hotkey")
        r = self._row(c1)
        ctk.CTkLabel(r, text=self.app._t("language"), width=100, anchor="w", **self.LABEL_KW).pack(side="left")
        self._lv = ctk.StringVar(value=self.app.lang)
        ctk.CTkOptionMenu(r, values=["auto","en","zh"], variable=self._lv, width=110).pack(side="left", padx=8)

        r = self._row(c1)
        ctk.CTkLabel(r, text=self.app._t("hotkey"), width=100, anchor="w", **self.LABEL_KW).pack(side="left")
        hf = ctk.CTkFrame(r, fg_color="transparent"); hf.pack(side="left")
        self._mv = ctk.StringVar(value="+".join(self.app.config.get("hotkey_modifiers", ["ctrl"])))
        ctk.CTkOptionMenu(hf, values=["ctrl","shift","alt","win","ctrl+shift","ctrl+alt","win+shift"],
                          variable=self._mv, width=110).pack(side="left")
        ctk.CTkLabel(hf, text="  +  ", **self.LABEL_KW).pack(side="left")
        self._kv = ctk.StringVar(value=self.app.config.get("hotkey_key", "V"))
        ctk.CTkOptionMenu(hf, values=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
                          variable=self._kv, width=60).pack(side="left")

        # ── File Naming ──
        c2 = self._setting_card(f, "File Naming")
        r = self._row(c2)
        ctk.CTkLabel(r, text=self.app._t("filename_prefix"), width=100, anchor="w", **self.LABEL_KW).pack(side="left")
        self._pv = ctk.StringVar(value=self.app.config.get("filename_prefix", "Screenshot"))
        ctk.CTkEntry(r, textvariable=self._pv, width=200).pack(side="left", padx=8)

        r = self._row(c2)
        ctk.CTkLabel(r, text=self.app._t("filename_rule"), width=100, anchor="w", **self.LABEL_KW).pack(side="left", anchor="n")
        rf = ctk.CTkFrame(r, fg_color="transparent"); rf.pack(side="left", fill="x", expand=True)
        self._rv = ctk.StringVar(value=self.app.config.get("filename_rule", "timestamp"))
        for rn in ["timestamp","datetime","date_seq","sequential"]:
            ctk.CTkRadioButton(rf, text=self.app._t(f"rule_{rn}"), variable=self._rv, value=rn,
                               font=("Segoe UI", 11)).pack(anchor="w", pady=1)

        # ── Image Settings ──
        c3 = self._setting_card(f, "Image Settings")
        r = self._row(c3)
        ctk.CTkLabel(r, text=self.app._t("image_format"), width=100, anchor="w", **self.LABEL_KW).pack(side="left")
        self._fv = ctk.StringVar(value=self.app.config.get("image_format", "png"))
        ctk.CTkOptionMenu(r, values=["png","jpg","bmp"], variable=self._fv, width=90).pack(side="left", padx=8)

        r = self._row(c3)
        ctk.CTkLabel(r, text=self.app._t("jpg_quality"), width=100, anchor="w", **self.LABEL_KW).pack(side="left")
        self._qv = ctk.IntVar(value=self.app.config.get("jpg_quality", 90))
        self._qs = ctk.CTkSlider(r, from_=10, to=100, variable=self._qv, width=160)
        self._qs.pack(side="left", padx=8)
        self._ql = ctk.CTkLabel(r, text=str(self._qv.get()), width=30, **self.LABEL_KW)
        self._ql.pack(side="left")
        self._qs.configure(command=lambda v: self._ql.configure(text=str(int(v))))

        # ── Features ──
        c4 = self._setting_card(f, "Other Features")
        for var, cfg_key, label in [
            ("_stv","save_video","save_video"), ("_stx","save_text","save_text"), ("_nv","show_notification","notifications")
        ]:
            r = self._row(c4)
            setattr(self, var, ctk.BooleanVar(value=self.app.config.get(cfg_key, False)))
            ctk.CTkSwitch(r, text=self.app._t(label), variable=getattr(self, var),
                          font=("Segoe UI", 11)).pack(side="left")

        # Buttons
        bf = ctk.CTkFrame(f, fg_color="transparent")
        bf.pack(fill="x", pady=(6, 10))
        ctk.CTkButton(bf, text=self.app._t("apply"), command=self._apply,
                       width=140, height=38, fg_color="#2563eb").pack(side="left", padx=(0, 10))
        ctk.CTkButton(bf, text=self.app._t("reset"), command=self._reset,
                       width=140, height=38, fg_color="gray40").pack(side="left")

    def _apply(self):
        a = self.app
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
        messagebox.showinfo(a._t("applied"), "")

    def _reset(self):
        self._lv.set("auto"); self._mv.set("ctrl"); self._kv.set("V")
        self._pv.set(self.app._t("cfg_prefix")); self._rv.set("timestamp")
        self._fv.set("png"); self._qv.set(90); self._ql.configure(text="90")
        self._stv.set(False); self._stx.set(False); self._nv.set(True)

    # ── About Tab ────────────────────────────
    def _build_about(self):
        p = ctk.CTkFrame(self.t_about, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=6, pady=4)
        f = ctk.CTkFrame(p, **self.CARD_KW)
        f.pack(fill="x", pady=(6, 0))

        logo = self._load_img(LOGO_PATH, max_w=480, max_h=120)
        if logo:
            ctk.CTkLabel(f, text="", image=logo).pack(pady=(28, 8))
        ctk.CTkLabel(f, text="Paste to Explorer", font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(f, text=f"Version 1.0.0", font=("Segoe UI", 11),
                     text_color="#888888").pack(pady=(2, 2))
        ctk.CTkLabel(f, text=self.app._t("about_desc"), font=("Segoe UI", 11),
                     text_color="#888888").pack(pady=(0, 16))
        ctk.CTkFrame(f, height=1, fg_color=("#e0e0e0","#3a3a3a")).pack(fill="x", padx=40)

        qr = self._load_qr()
        if qr:
            ctk.CTkLabel(f, text="", image=qr).pack(pady=(16, 4))
        ctk.CTkLabel(f, text=self.app._t("about_support"), font=("Segoe UI", 11, "italic"),
                     text_color="#888888").pack(pady=(4, 20))

    def _load_img(self, path, max_w=500, max_h=200):
        if path and path.exists():
            try:
                img = Image.open(path); w, h = img.size
                sc = min(max_w / w, max_h / h, 1.0)
                nw, nh = int(w * sc), int(h * sc)
                return ctk.CTkImage(img.resize((nw, nh), Image.LANCZOS), size=(nw, nh))
            except: pass
        return None

    def _load_qr(self):
        # Check multiple locations for zanshang.png
        for p in [Path("assets/zanshang.png"), Path("zanshang.png"),
                  ASSETS_DIR / "zanshang.png", APP_DIR / "zanshang.png"]:
            try:
                if p.exists():
                    img = Image.open(p)
                    img.thumbnail((200, 200), Image.LANCZOS)
                    return ctk.CTkImage(img, size=img.size)
            except: pass
        # Also check relative to app/assets for packaged mode
        try:
            for p in [APP_DIR / "assets" / "zanshang.png", APP_DIR / "zanshang.png"]:
                if p.exists():
                    img = Image.open(p); img.thumbnail((200,200), Image.LANCZOS)
                    return ctk.CTkImage(img, size=img.size)
        except: pass
        return None


if __name__ == "__main__":
    App().run()
