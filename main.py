from __future__ import annotations

import argparse
import ctypes
import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import messagebox, ttk

import pyperclip
import pystray
from PIL import Image, ImageDraw
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController

from config import load_settings, save_settings
from translator import TranslationError, translate


class SelectionTranslatorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.events: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self.settings = load_settings()
        self.keyboard_controller = KeyboardController()
        self.mouse_controller = MouseController()
        self.busy = False
        self.settings_window: tk.Toplevel | None = None
        self.tray_icon: pystray.Icon | None = None
        self.hotkey_listener = keyboard.GlobalHotKeys(
            {
                "<alt>+q": self.queue_translation,
                "<alt>+<shift>+q": self.queue_settings,
            }
        )

    def run(self) -> None:
        self.hotkey_listener.start()
        self.start_tray_icon()
        self.root.after(50, self.process_events)
        if not self.has_credentials():
            self.root.after(100, self.show_settings)
        self.root.mainloop()

    def has_credentials(self) -> bool:
        return bool(
            self.settings["appid"].isdigit() and self.settings["secret_key"]
        )

    def queue_translation(self) -> None:
        self.events.put(("translate", None))

    def queue_settings(self) -> None:
        self.events.put(("settings", None))

    def process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "translate":
                    self.begin_translation()
                elif event == "settings":
                    self.show_settings()
                elif event == "translation":
                    self.busy = False
                    self.show_popup("译文", value or "")
                elif event == "notice":
                    self.busy = False
                    self.show_popup("划词翻译", value or "")
                elif event == "quit":
                    self.shutdown()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self.process_events)

    def begin_translation(self) -> None:
        if self.busy:
            return
        if not self.has_credentials():
            self.show_settings()
            return
        self.busy = True
        threading.Thread(target=self.translate_selection, daemon=True).start()

    def translate_selection(self) -> None:
        try:
            selected_text = self.copy_selected_text()
            if not selected_text:
                self.events.put(("notice", "没有获取到选中的文本。"))
                return
            translated_text = translate(
                selected_text,
                self.settings["appid"],
                self.settings["secret_key"],
                self.settings["target_lang"],
            )
            self.events.put(("translation", translated_text))
        except TranslationError as error:
            self.events.put(("notice", str(error)))
        except pyperclip.PyperclipException:
            self.events.put(("notice", "无法访问 Windows 剪贴板。"))
        except Exception:
            self.events.put(("notice", "翻译失败，请检查网络和 API 配置。"))

    def copy_selected_text(self) -> str:
        self.wait_for_shortcut_release()
        original_clipboard_text = pyperclip.paste()
        marker = f"__selection_translator_{uuid.uuid4().hex}__"
        pyperclip.copy(marker)
        try:
            self.keyboard_controller.press(keyboard.Key.ctrl)
            self.keyboard_controller.press("c")
            self.keyboard_controller.release("c")
            self.keyboard_controller.release(keyboard.Key.ctrl)

            deadline = time.monotonic() + 0.8
            while time.monotonic() < deadline:
                selected_text = pyperclip.paste()
                if selected_text != marker:
                    return selected_text.strip()
                time.sleep(0.01)
            return ""
        finally:
            pyperclip.copy(original_clipboard_text)

    @staticmethod
    def wait_for_shortcut_release() -> None:
        virtual_keys = (0x12, 0xA4, 0xA5, 0x10, 0x11, 0x51)
        deadline = time.monotonic() + 0.8
        while time.monotonic() < deadline:
            pressed = any(ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000 for key in virtual_keys)
            if not pressed:
                return
            time.sleep(0.01)

    def show_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("划词翻译设置")
        window.resizable(False, False)
        window.attributes("-topmost", True)
        window.columnconfigure(1, weight=1)
        window.protocol("WM_DELETE_WINDOW", self.close_settings)

        appid_var = tk.StringVar(value=self.settings["appid"])
        secret_key_var = tk.StringVar(value=self.settings["secret_key"])
        target_label = "简体中文" if self.settings["target_lang"] == "zh" else "英文"
        target_var = tk.StringVar(value=target_label)

        ttk.Label(window, text="百度 APP ID").grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")
        ttk.Entry(window, textvariable=appid_var, width=42).grid(
            row=0, column=1, padx=(0, 16), pady=(16, 8), sticky="ew"
        )
        ttk.Label(window, text="百度密钥").grid(row=1, column=0, padx=16, pady=8, sticky="w")
        ttk.Entry(window, textvariable=secret_key_var, show="*", width=42).grid(
            row=1, column=1, padx=(0, 16), pady=8, sticky="ew"
        )
        ttk.Label(window, text="翻译目标").grid(row=2, column=0, padx=16, pady=8, sticky="w")
        target_box = ttk.Combobox(
            window,
            textvariable=target_var,
            values=("简体中文", "英文"),
            state="readonly",
            width=18,
        )
        target_box.grid(row=2, column=1, padx=(0, 16), pady=8, sticky="w")
        ttk.Label(
            window,
            text="Alt+Q 直接翻译选区，无需手动复制；Alt+Shift+Q 打开此设置。\n百度 APP ID 是后台显示的纯数字应用 ID，不是密钥。",
            justify="left",
        ).grid(row=3, column=0, columnspan=2, padx=16, pady=(4, 12), sticky="w")

        def save() -> None:
            appid = appid_var.get().strip()
            secret_key = secret_key_var.get().strip()
            if not appid or not secret_key:
                messagebox.showerror("无法保存", "请填写百度 APP ID 和密钥。", parent=window)
                return
            if not appid.isdigit():
                messagebox.showerror("APP ID 不正确", "百度 APP ID 应为后台显示的纯数字应用 ID，不是密钥。", parent=window)
                return
            target_lang = "zh" if target_var.get() == "简体中文" else "en"
            try:
                save_settings(appid, secret_key, target_lang)
            except OSError:
                messagebox.showerror("无法保存", "无法写入本机配置文件。", parent=window)
                return
            self.settings = load_settings()
            self.close_settings()

        button_frame = ttk.Frame(window)
        button_frame.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="e")
        ttk.Button(button_frame, text="取消", command=self.close_settings).pack(side="right")
        ttk.Button(button_frame, text="保存", command=save).pack(side="right", padx=(0, 8))

    def close_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None

    def show_popup(self, title: str, content: str) -> None:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.attributes("-topmost", True)
        window.resizable(False, False)
        window.bind("<Escape>", lambda _: window.destroy())

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, font=("Microsoft YaHei UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        text_box = tk.Text(text_frame, width=56, height=12, wrap="word", borderwidth=0)
        scrollbar = ttk.Scrollbar(text_frame, command=text_box.yview)
        text_box.configure(yscrollcommand=scrollbar.set)
        text_box.insert("1.0", content)
        text_box.configure(state="disabled")
        text_box.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(button_frame, text="关闭", command=window.destroy).pack(side="right")
        if title == "译文":
            ttk.Button(
                button_frame,
                text="复制译文",
                command=lambda: pyperclip.copy(content),
            ).pack(side="right", padx=(0, 8))

        window.update_idletasks()
        cursor_x, cursor_y = self.mouse_controller.position
        max_x = max(0, window.winfo_screenwidth() - window.winfo_reqwidth())
        max_y = max(0, window.winfo_screenheight() - window.winfo_reqheight())
        window.geometry(f"+{min(cursor_x + 16, max_x)}+{min(cursor_y + 16, max_y)}")
        window.after(12000, window.destroy)

    def start_tray_icon(self) -> None:
        image = Image.new("RGB", (64, 64), "#2563EB")
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((16, 14, 48, 50), fill="#FFFFFF")
        drawing.line((22, 27, 42, 27), fill="#2563EB", width=4)
        drawing.line((22, 37, 36, 37), fill="#2563EB", width=4)
        menu = pystray.Menu(
            pystray.MenuItem("打开设置", lambda *_: self.events.put(("settings", None))),
            pystray.MenuItem("退出", lambda *_: self.events.put(("quit", None))),
        )
        self.tray_icon = pystray.Icon("selection_translator", image, "划词翻译", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def shutdown(self) -> None:
        self.hotkey_listener.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        load_settings()
        print("依赖和配置模块检查通过。")
        return
    SelectionTranslatorApp().run()


if __name__ == "__main__":
    main()
