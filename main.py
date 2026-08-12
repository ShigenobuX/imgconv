import argparse
import ctypes
import json
import os
import sys
import threading
import tkinter as tk
import winreg
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

import pillow_heif

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

DND_AVAILABLE = TkinterDnD is not None and DND_FILES is not None

APP_VERSION = "0.9.2"


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstallerの一時ディレクトリを優先的に使用
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

try:
    from win11toast import toast as win11toast_toast
    ToastNotifier = None
except ImportError:
    win11toast_toast = None
    try:
        from win11toast import ToastNotifier
    except ImportError:
        ToastNotifier = None

SUPPORTED_INPUT_EXTENSIONS = {
    ".heic",
    ".heif",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".ico",
}
SUPPORTED_OUTPUT_FORMATS = {
    "jpg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
}
CONTEXT_MENU_BASE = r"Software\Classes\*\shell"
ICON_FILENAME = "imgconv.ico"
MENU_ICON = os.path.join(get_app_dir(), ICON_FILENAME)
FORMAT_MENU_ITEMS = [
    ("jpg", "JPGに変換 (品質85%)"),
    ("png", "PNGに変換"),
    ("webp", "WEBPに変換"),
    ("bmp", "BMPに変換"),
]
MENU_KEY_NAMES = [f"ImageFormatConvert_{fmt}" for fmt, _ in FORMAT_MENU_ITEMS]
LEGACY_MENU_KEYS = ["ImageFormatConvert"]
DEFAULT_MENU_FORMATS = [fmt for fmt, _ in FORMAT_MENU_ITEMS]
CONFIG_FILENAME = "settings.json"
SETTINGS_PATH = os.path.join(get_app_dir(), CONFIG_FILENAME)

pillow_heif.register_heif_opener()


def load_user_settings() -> dict[str, str]:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_user_settings(settings: dict[str, str]) -> None:
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def show_notification(title: str, message: str) -> None:
    if ToastNotifier is not None:
        try:
            notifier = ToastNotifier()
            notifier.show_toast(title, message, duration=5)
            return
        except Exception:
            pass
    if win11toast_toast is not None:
        try:
            win11toast_toast(title=title, msg=message, duration=5)
            return
        except Exception:
            pass
    print(f"{title}: {message}")


def get_default_python_command() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable


def get_default_script_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    if not sys.argv or sys.argv[0] in ("", "-c"):
        return os.path.abspath(__file__)
    return os.path.abspath(sys.argv[0])


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def format_command_for_menu(format_key: str) -> str:
    executable = get_default_python_command()
    script_path = get_default_script_path()
    if getattr(sys, "frozen", False):
        return f'"{executable}" --convert-to {format_key} "%1"'
    return f'"{executable}" "{script_path}" --convert-to {format_key} "%1"'


def create_context_menu(selected_formats: list[str] | None = None) -> None:
    if os.name != "nt":
        raise RuntimeError("Context menu registration is supported only on Windows.")

    if not os.path.exists(MENU_ICON):
        raise FileNotFoundError(f"Icon file not found: {MENU_ICON}")

    if selected_formats is None:
        selected_formats = DEFAULT_MENU_FORMATS

    root_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_BASE)
    try:
        for fmt, label in FORMAT_MENU_ITEMS:
            if fmt not in selected_formats:
                continue
            menu_name = f"ImageFormatConvert_{fmt}"
            item_key = winreg.CreateKey(root_key, menu_name)
            winreg.SetValueEx(item_key, "MUIVerb", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(item_key, "Icon", 0, winreg.REG_SZ, MENU_ICON)
            command_key = winreg.CreateKey(item_key, "command")
            winreg.SetValueEx(command_key, None, 0, winreg.REG_SZ, format_command_for_menu(fmt))
            command_key.Close()
            item_key.Close()
    finally:
        root_key.Close()


def _delete_registry_tree(root: int, sub_key: str) -> None:
    try:
        with winreg.OpenKey(root, sub_key, 0, winreg.KEY_READ) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_registry_tree(root, os.path.join(sub_key, child))
        winreg.DeleteKey(root, sub_key)
    except FileNotFoundError:
        pass


def remove_context_menu() -> None:
    if os.name != "nt":
        raise RuntimeError("Context menu unregistration is supported only on Windows.")

    for key_name in MENU_KEY_NAMES + LEGACY_MENU_KEYS:
        _delete_registry_tree(winreg.HKEY_CURRENT_USER, os.path.join(CONTEXT_MENU_BASE, key_name))


def normalize_paths_from_drag(data: str) -> list[str]:
    if not data:
        return []
    data = data.strip()
    if data.startswith("{") and data.endswith("}"):
        data = data[1:-1]
    paths = []
    item = ""
    in_brace = False
    for char in data:
        if char == "{":
            in_brace = True
            item = ""
            continue
        if char == "}":
            in_brace = False
            paths.append(item)
            item = ""
            continue
        if in_brace:
            item += char
            continue
        if char.isspace():
            if item:
                paths.append(item)
                item = ""
            continue
        item += char
    if item:
        paths.append(item)
    return [p for p in paths if p]


def scan_input_files(paths: list[str]) -> list[str]:
    found = []
    seen = set()
    for path in paths:
        path = os.path.normpath(path.strip('"'))
        if not path:
            continue
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in SUPPORTED_INPUT_EXTENSIONS:
                        candidate = os.path.join(root, name)
                        if candidate not in seen:
                            seen.add(candidate)
                            found.append(candidate)
        elif os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_INPUT_EXTENSIONS and path not in seen:
                seen.add(path)
                found.append(path)
    return found


def build_output_path(input_path: str, output_dir: str, output_ext: str) -> str:
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    candidate = os.path.join(output_dir, f"{base_name}{output_ext}")
    index = 1
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{base_name}_{index}{output_ext}")
        index += 1
    return candidate


def convert_image(
    input_path: str,
    output_format: str,
    quality: int,
    preserve_exif: bool,
    resize_width: int | None,
    resize_height: int | None,
    keep_aspect: bool,
    output_folder: str | None = None,
) -> tuple[bool, str]:
    try:
        with Image.open(input_path) as image:
            image = ImageOps.exif_transpose(image)
            original_format = image.format
            exif_data = image.info.get("exif") if preserve_exif else None

            if resize_width or resize_height:
                original_width, original_height = image.size
                if keep_aspect:
                    if resize_width and resize_height:
                        ratio = min(resize_width / original_width, resize_height / original_height)
                        new_width = max(1, int(original_width * ratio))
                        new_height = max(1, int(original_height * ratio))
                    elif resize_width:
                        ratio = resize_width / original_width
                        new_width = resize_width
                        new_height = max(1, int(original_height * ratio))
                    elif resize_height:
                        ratio = resize_height / original_height
                        new_height = resize_height
                        new_width = max(1, int(original_width * ratio))
                else:
                    new_width = resize_width or original_width
                    new_height = resize_height or original_height
                image = image.resize((new_width, new_height), Image.LANCZOS)

            output_ext = ".jpg" if output_format == "JPEG" else f".{output_format.lower()}"
            target_dir = output_folder or os.path.dirname(input_path)
            os.makedirs(target_dir, exist_ok=True)
            output_path = build_output_path(input_path, target_dir, output_ext)

            save_kwargs = {}
            if output_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = max(10, min(100, quality))
            if exif_data and output_format in ("JPEG", "WEBP"):
                save_kwargs["exif"] = exif_data

            if output_format == "JPEG" and image.mode in ("RGBA", "LA", "P", "RGBa"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                alpha = image.convert("RGBA").split()[-1]
                background.paste(image.convert("RGBA"), mask=alpha)
                image = background
            elif output_format == "JPEG" and image.mode != "RGB":
                image = image.convert("RGB")
            elif output_format in ("BMP",) and image.mode == "RGBA":
                image = image.convert("RGB")

            image.save(output_path, format=output_format, **save_kwargs)
            return True, output_path
    except Exception as exc:
        return False, str(exc)


def run_headless_conversion(format_key: str, paths: list[str], quality: int = 85, preserve_exif: bool = True) -> None:
    all_files = scan_input_files(paths)
    if not all_files:
        raise FileNotFoundError("No supported input files were found.")

    successes = 0
    failures = 0
    for file_path in all_files:
        success, message = convert_image(
            file_path,
            SUPPORTED_OUTPUT_FORMATS[format_key],
            quality,
            preserve_exif,
            None,
            None,
            True,
            None,
        )
        if success:
            successes += 1
        else:
            failures += 1
            print(f"Failed: {file_path} -> {message}")

    message = f"{successes}件の変換が完了しました。"
    if failures:
        message += f" {failures}件は失敗しました。"
    show_notification("変換完了", message)


def parse_command_line() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Windows向け 画像フォーマットコンバーター")
    parser.add_argument("--convert-to", choices=SUPPORTED_OUTPUT_FORMATS.keys(), help="バックグラウンド変換を実行する出力形式")
    parser.add_argument("paths", nargs="*", help="変換対象のファイルまたはフォルダパス")
    parser.add_argument("--register-menu", action="store_true", help="右クリックメニューを登録する")
    parser.add_argument("--unregister-menu", action="store_true", help="右クリックメニューを解除する")
    parser.add_argument("--quality", type=int, default=85, help="JPEG/WEBP変換時の画質(1-100)")
    return parser.parse_args()


class ImageConverterApp:
    def __init__(self):
        settings = load_user_settings()
        theme = settings.get("theme", "System")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.root = TkinterDnD.Tk() if TkinterDnD else ctk.CTk()
        self.root.title(f"画像フォーマットコンバーター v {APP_VERSION}")
        try:
            self.root.iconbitmap(MENU_ICON)
        except Exception:
            pass
        self.root.geometry(settings.get("geometry", "950x700"))
        self.root.minsize(900, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.selected_files: list[str] = []
        self.output_format_var = tk.StringVar(value="jpg")
        self.quality_var = tk.IntVar(value=85)
        self.preserve_exif_var = tk.BooleanVar(value=True)
        self.resize_width_var = tk.StringVar(value="")
        self.resize_height_var = tk.StringVar(value="")
        self.keep_aspect_var = tk.BooleanVar(value=True)
        self.save_destination_var = tk.StringVar(value="same")
        self.custom_save_folder = tk.StringVar(value="")
        self.theme_var = tk.StringVar(value=ctk.get_appearance_mode())
        self.menu_format_vars = {fmt: tk.BooleanVar(value=True) for fmt, _ in FORMAT_MENU_ITEMS}

        self._create_widgets()
        self._layout_widgets()
        self._bind_events()
        self._apply_theme_styles()
        self._configure_listbox_theme()

        self.worker_thread: threading.Thread | None = None

    def _create_widgets(self) -> None:
        self.top_frame = ctk.CTkFrame(self.root)
        self.bottom_frame = ctk.CTkFrame(self.root)

        self.settings_button = ctk.CTkButton(
            self.top_frame,
            text="設定",
            command=self._open_settings,
            fg_color="#6d6d6d",
            hover_color="#5a5a5a",
            text_color="#ffffff",
        )

        self.drag_label = ctk.CTkLabel(
            self.top_frame,
            text="ウィンドウ内のどこでもファイルをドロップできます",
            anchor="w",
            height=30,
            fg_color="transparent",
        )
        self.file_panel_frame = ctk.CTkFrame(self.root)
        self.file_button_panel = ctk.CTkFrame(self.file_panel_frame)
        self.file_listbox = tk.Listbox(self.file_panel_frame, selectmode=tk.EXTENDED, activestyle="none")
        self.list_scroll = ctk.CTkScrollbar(self.file_panel_frame, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=self.list_scroll.set)

        if not DND_AVAILABLE:
            self.drag_label.configure(text="ドラッグ＆ドロップは未対応です。ファイル追加ボタンを使用してください。")

        self.add_files_button = ctk.CTkButton(self.file_button_panel, text="ファイルを追加", command=self._add_files)
        self.add_folder_button = ctk.CTkButton(self.file_button_panel, text="フォルダを追加", command=self._add_folder)
        self.remove_selected_button = ctk.CTkButton(self.file_button_panel, text="選択を削除", command=self._remove_selected)
        self.clear_list_button = ctk.CTkButton(self.file_button_panel, text="リストをクリア", command=self._clear_list)

        self.options_frame = ctk.CTkFrame(
            self.root,
            fg_color="#f2f2f2",
            border_width=1,
            border_color="#d0d0d0",
        )
        self.output_format_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["jpg", "png", "webp", "bmp"],
            variable=self.output_format_var,
        )
        self.quality_slider = ctk.CTkSlider(self.options_frame, from_=10, to=100, variable=self.quality_var)
        self.quality_label = ctk.CTkLabel(self.options_frame, text="画質: 85")
        self.exif_checkbox = ctk.CTkCheckBox(self.options_frame, text="Exif情報を保持する", variable=self.preserve_exif_var)
        self.resize_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.resize_title_label = ctk.CTkLabel(self.resize_frame, text="リサイズ（ピクセル指定）")
        self.width_label = ctk.CTkLabel(self.resize_frame, text="幅 (px)")
        self.width_entry = ctk.CTkEntry(self.resize_frame, placeholder_text="入力", textvariable=self.resize_width_var, width=120)
        self.height_label = ctk.CTkLabel(self.resize_frame, text="高さ (px)")
        self.height_entry = ctk.CTkEntry(self.resize_frame, placeholder_text="入力", textvariable=self.resize_height_var, width=120)
        self.keep_aspect_checkbox = ctk.CTkCheckBox(self.options_frame, text="アスペクト比を維持", variable=self.keep_aspect_var)

        self.save_option_same = ctk.CTkRadioButton(self.options_frame, text="元ファイルと同じフォルダ", variable=self.save_destination_var, value="same")
        self.save_option_custom = ctk.CTkRadioButton(self.options_frame, text="指定フォルダに保存", variable=self.save_destination_var, value="custom")
        self.select_save_folder_button = ctk.CTkButton(self.options_frame, text="保存先を選択", command=self._select_save_folder)
        self.save_folder_label = ctk.CTkLabel(self.options_frame, textvariable=self.custom_save_folder)

        self.convert_button = ctk.CTkButton(
            self.bottom_frame,
            text="変換を開始",
            command=self._start_conversion,
            fg_color="#d9534f",
            hover_color="#c9302c",
            width=220,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(self.bottom_frame, text="準備完了")
        self.log_box = ctk.CTkTextbox(self.root, height=170, state="disabled")

    def _layout_widgets(self) -> None:
        self.top_frame.pack(fill="x", padx=16, pady=(16, 0))
        self.drag_label.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=(8, 8))
        self.settings_button.pack(side="right", pady=(8, 8))

        self.file_panel_frame.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 8))
        self.file_button_panel.pack(fill="x", pady=(0, 8))
        self.add_files_button.pack(fill="x", padx=0, pady=(0, 4))
        self.add_folder_button.pack(fill="x", padx=0, pady=4)
        self.remove_selected_button.pack(fill="x", padx=0, pady=4)
        self.clear_list_button.pack(fill="x", padx=0, pady=(4, 0))
        self.file_listbox.pack(side="left", fill="both", expand=True, pady=(0, 8))
        self.list_scroll.pack(side="left", fill="y", padx=(8, 16), pady=(0, 8))

        self.options_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(self.options_frame, text="変換設定", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(8, 4))
        ctk.CTkLabel(self.options_frame, text="出力形式").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        self.output_format_menu.grid(row=1, column=1, sticky="ew", padx=8, pady=8)
        ctk.CTkLabel(self.options_frame, text="画質 (JPEG/WEBP)").grid(row=2, column=0, sticky="w", padx=8, pady=8)
        self.quality_slider.grid(row=2, column=1, sticky="ew", padx=8, pady=8)
        self.quality_label.grid(row=2, column=2, sticky="w", padx=8, pady=8)
        self.exif_checkbox.grid(row=3, column=0, columnspan=5, sticky="w", padx=8, pady=8)
        self.resize_frame.grid(row=4, column=0, columnspan=5, sticky="w", padx=8, pady=8)
        self.resize_title_label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.width_label.grid(row=0, column=1, sticky="w", padx=(0, 4))
        self.width_entry.grid(row=0, column=2, sticky="w", padx=(0, 12))
        self.height_label.grid(row=0, column=3, sticky="w", padx=(0, 4))
        self.height_entry.grid(row=0, column=4, sticky="w")
        self.keep_aspect_checkbox.grid(row=5, column=0, columnspan=5, sticky="w", padx=8, pady=8)
        self.save_option_same.grid(row=6, column=0, columnspan=5, sticky="w", padx=8, pady=8)
        self.save_option_custom.grid(row=7, column=0, sticky="w", padx=8, pady=8)
        self.select_save_folder_button.grid(row=7, column=1, sticky="w", padx=8, pady=8)
        self.save_folder_label.grid(row=7, column=2, columnspan=3, sticky="w", padx=8, pady=8)
        self.options_frame.grid_columnconfigure(1, weight=0)
        self.options_frame.grid_columnconfigure(2, weight=0)
        self.options_frame.grid_columnconfigure(3, weight=0)
        self.options_frame.grid_columnconfigure(4, weight=0)
        self.resize_frame.grid_columnconfigure(2, weight=0)
        self.resize_frame.grid_columnconfigure(4, weight=0)

        self.bottom_frame.pack(fill="x", padx=16, pady=(0, 8))
        self.convert_button.pack(pady=8)
        self.progress_bar.pack(fill="x", padx=8, pady=8)
        self.status_label.pack(fill="x", padx=8, pady=(0, 8))
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _bind_events(self) -> None:
        self.quality_var.trace_add("write", self._update_quality_label)
        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self._log_message("注意: ドラッグ＆ドロップは現在利用できません。ファイル追加ボタンを使用してください。")
        self.file_listbox.bind("<Double-Button-1>", lambda event: self._remove_selected())

    def _configure_listbox_theme(self) -> None:
        try:
            if self.theme_var.get() == "Dark":
                self.file_listbox.configure(
                    bg="#1e1e1e",
                    fg="#f5f5f5",
                    selectbackground="#3b3b3b",
                    selectforeground="#ffffff",
                    highlightbackground="#2c2c2c",
                    highlightcolor="#2c2c2c",
                    borderwidth=1,
                    relief="solid",
                )
            else:
                self.file_listbox.configure(
                    bg="#ffffff",
                    fg="#000000",
                    selectbackground="#c8c8c8",
                    selectforeground="#000000",
                    highlightbackground="#d9d9d9",
                    highlightcolor="#d9d9d9",
                    borderwidth=1,
                    relief="solid",
                )
        except tk.TclError:
            pass

    def _apply_theme_styles(self) -> None:
        if self.theme_var.get() == "Dark":
            if isinstance(self.root, ctk.CTk):
                self.root.configure(fg_color="#101010")
            else:
                self.root.configure(bg="#101010")
            self.top_frame.configure(fg_color="#141414")
            self.bottom_frame.configure(fg_color="#141414")
            self.options_frame.configure(fg_color="#1f1f1f", border_color="#2a2a2a")
            self.drag_label.configure(fg_color=("#181818", "#1d1d1d"))
        else:
            if isinstance(self.root, ctk.CTk):
                self.root.configure(fg_color="#f0f0f0")
            else:
                self.root.configure(bg="#f0f0f0")
            self.top_frame.configure(fg_color="#f0f0f0")
            self.bottom_frame.configure(fg_color="#f0f0f0")
            self.options_frame.configure(fg_color="#f2f2f2", border_color="#d0d0d0")
            self.drag_label.configure(fg_color=("#f0f0f0", "#d9d9d9"))

    def _update_quality_label(self, *_args) -> None:
        self.quality_label.configure(text=f"画質: {self.quality_var.get()}")

    def _register_menu(self) -> None:
        try:
            selected_formats = [fmt for fmt, var in self.menu_format_vars.items() if var.get()]
            create_context_menu(selected_formats)
            messagebox.showinfo("登録完了", "右クリックメニューを登録しました。")
        except Exception as exc:
            messagebox.showerror("登録エラー", str(exc))

    def _unregister_menu(self) -> None:
        try:
            remove_context_menu()
            messagebox.showinfo("解除完了", "右クリックメニューを解除しました。")
        except Exception as exc:
            messagebox.showerror("解除エラー", str(exc))

    def _open_settings(self) -> None:
        if getattr(self, "settings_window", None) is not None:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.attributes("-topmost", True)
            self.settings_window.after(0, lambda: self.settings_window.attributes("-topmost", False))
            self.settings_window.focus_force()
            return

        self.settings_window = ctk.CTkToplevel(self.root)
        self.settings_window.title("設定")
        self.settings_window.geometry("420x520")
        self.settings_window.protocol("WM_DELETE_WINDOW", self._close_settings)
        self.settings_window.transient(self.root)
        self.settings_window.grab_set()
        self.settings_window.attributes("-topmost", True)
        self.settings_window.after(0, lambda: self.settings_window.attributes("-topmost", False))

        menu_group = ctk.CTkFrame(self.settings_window)
        menu_group.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(menu_group, text="右クリックメニュー", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(menu_group, text="登録する拡張子を選択し、操作を実行してください").pack(anchor="w", pady=(0, 8))
        for fmt, label in FORMAT_MENU_ITEMS:
            ctk.CTkCheckBox(
                menu_group,
                text=label,
                variable=self.menu_format_vars[fmt],
            ).pack(anchor="w", padx=8, pady=4)

        button_row = ctk.CTkFrame(menu_group)
        button_row.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(button_row, text="登録", command=self._register_menu).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(button_row, text="解除", command=self._unregister_menu).pack(side="left", expand=True, fill="x", padx=(8, 0))

        theme_group = ctk.CTkFrame(self.settings_window)
        theme_group.pack(fill="x", padx=16, pady=(8, 16))
        ctk.CTkLabel(theme_group, text="テーマ", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(theme_group, text="アプリの見た目を選択してください").pack(anchor="w", pady=(0, 8))
        theme_frame = ctk.CTkFrame(theme_group)
        theme_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkRadioButton(theme_frame, text="システム", variable=self.theme_var, value="System", command=self._apply_theme).pack(side="left", padx=8, pady=8)
        ctk.CTkRadioButton(theme_frame, text="ライト", variable=self.theme_var, value="Light", command=self._apply_theme).pack(side="left", padx=8, pady=8)
        ctk.CTkRadioButton(theme_frame, text="ダーク", variable=self.theme_var, value="Dark", command=self._apply_theme).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(self.settings_window, text="閉じる", command=self._close_settings).pack(pady=16)

    def _close_settings(self) -> None:
        if getattr(self, "settings_window", None) is None:
            return
        self.settings_window.destroy()
        self.settings_window = None

    def _apply_theme(self) -> None:
        ctk.set_appearance_mode(self.theme_var.get())
        self._apply_theme_styles()
        self._configure_listbox_theme()
        self._save_settings()

    def _save_settings(self) -> None:
        save_user_settings(
            {
                "theme": self.theme_var.get(),
                "geometry": self.root.geometry(),
            }
        )

    def _on_close(self) -> None:
        self._save_settings()
        self.root.destroy()

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="画像ファイルを選択",
            filetypes=[
                ("サポート対象ファイル", "*.heic *.heif *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif *.ico"),
                ("すべてのファイル", "*.*"),
            ],
        )
        self._append_files(list(paths))

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            self._append_files([folder])

    def _select_save_folder(self) -> None:
        folder = filedialog.askdirectory(title="保存先フォルダを選択")
        if folder:
            self.custom_save_folder.set(folder)
            self.save_destination_var.set("custom")

    def _append_files(self, paths: list[str]) -> None:
        new_files = scan_input_files(paths)
        added = 0
        for file_path in new_files:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                self.file_listbox.insert(tk.END, file_path)
                added += 1
        if added:
            self._log_message(f"{added} 件のファイルを追加しました。")
        else:
            self._log_message("追加可能な新しいファイルはありませんでした。")

    def _remove_selected(self) -> None:
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices:
            return
        for index in reversed(selected_indices):
            file_path = self.file_listbox.get(index)
            self.selected_files.remove(file_path)
            self.file_listbox.delete(index)
        self._log_message(f"{len(selected_indices)} 件をリストから削除しました。")

    def _clear_list(self) -> None:
        self.selected_files.clear()
        self.file_listbox.delete(0, tk.END)
        self._log_message("ファイルリストをクリアしました。")

    def _on_drop(self, event: tk.Event) -> None:
        paths = normalize_paths_from_drag(event.data)
        self._append_files(paths)

    def _start_conversion(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("実行中", "変換処理が既に実行中です。完了までお待ちください。")
            return
        if not self.selected_files:
            messagebox.showwarning("ファイルなし", "変換するファイルが選択されていません。")
            return
        if self.save_destination_var.get() == "custom" and not self.custom_save_folder.get():
            messagebox.showwarning("保存先未選択", "保存先フォルダを選択してください。")
            return

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _worker_loop(self) -> None:
        total = len(self.selected_files)
        success_count = 0
        fail_count = 0

        output_folder = self.custom_save_folder.get() if self.save_destination_var.get() == "custom" else None
        output_format = SUPPORTED_OUTPUT_FORMATS[self.output_format_var.get()]
        quality = self.quality_var.get()
        preserve_exif = self.preserve_exif_var.get()
        resize_width = self._parse_int(self.resize_width_var.get())
        resize_height = self._parse_int(self.resize_height_var.get())
        keep_aspect = self.keep_aspect_var.get()

        self._update_status("変換を開始します。")
        self._set_progress(0)

        for index, file_path in enumerate(self.selected_files, start=1):
            self._update_status(f"変換中: {os.path.basename(file_path)} ({index}/{total})")
            success, info = convert_image(
                file_path,
                output_format,
                quality,
                preserve_exif,
                resize_width,
                resize_height,
                keep_aspect,
                output_folder,
            )
            if success:
                success_count += 1
                self._log_message(f"成功: {info}")
            else:
                fail_count += 1
                self._log_message(f"失敗: {file_path} - {info}")
            self._set_progress(index / total)

        message = f"{success_count} 件の変換が完了しました。"
        if fail_count:
            message += f" {fail_count} 件は失敗しました。"
        self._update_status("処理が完了しました。")
        self._log_message(message)
        show_notification("変換完了", message)

    def _set_progress(self, value: float) -> None:
        self.root.after(0, lambda: self.progress_bar.set(value))

    def _update_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_label.configure(text=message))

    def _log_message(self, message: str) -> None:
        def append_log() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, append_log)

    @staticmethod
    def _parse_int(value: str) -> int | None:
        try:
            normalized = int(value)
            return normalized if normalized > 0 else None
        except Exception:
            return None

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    args = parse_command_line()

    if args.register_menu:
        create_context_menu()
        print("右クリックメニューを登録しました。")
        return

    if args.unregister_menu:
        remove_context_menu()
        print("右クリックメニューを解除しました。")
        return

    if args.convert_to:
        if not args.paths:
            raise SystemExit("変換対象のファイルを指定してください。")
        run_headless_conversion(args.convert_to, args.paths, quality=args.quality)
        return

    app = ImageConverterApp()
    app.run()


if __name__ == "__main__":
    main()
