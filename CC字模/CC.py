import io
import json
import os
import glob
import sys
import tempfile
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np

# resources.py 会在打包前由 build.py 自动生成，包含内嵌的图片二进制数据（base64）
# 在运行时优先从 resources 中读取，如不存在则回退到磁盘文件
try:
    import resources
except Exception:
    resources = None


class ImageToFontConverter:
    # 屏幕尺寸硬上限 ("16K 屏幕"字面含义)
    _MAX_DIM = 16384

    def __init__(self, root):
        self.root = root
        self.root.title("图像转字模工具")
        self.root.geometry("1400x900")

        # 设置窗口图标
        self.set_window_icon()

        # 屏幕尺寸 (W, H 必须是 8 的倍数；非 8 倍会 pad)
        self.width = tk.IntVar(value=128)
        self.height = tk.IntVar(value=64)
        self._W = 128  # pad 后的实际宽度
        self._H = 64   # pad 后的实际高度
        self._was_padded = False

        # 存储参数
        self.brightness = tk.DoubleVar(value=0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.scan_direction = tk.StringVar(value="vertical")
        self.scan_order = tk.StringVar(value="left_to_right_top_to_bottom")
        self.invert_color = tk.BooleanVar(value=False)
        self.rotation = tk.StringVar(value="0")
        self.horizontal_flip = tk.BooleanVar(value=False)
        self.vertical_flip = tk.BooleanVar(value=False)
        self.slideshow_interval = tk.IntVar(value=500)
        self.video_frame_interval = tk.IntVar(value=30)
        self.image_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.video_file = tk.StringVar()

        # 幻灯片播放相关
        self.slideshow_images = []
        self.slideshow_index = 0
        self.slideshow_running = False
        self.slideshow_job = None

        # 当前显示的图像
        self.current_image = None
        self.processed_image = None

        # 临时文件、后台线程、防抖、暂停
        self._icon_temp_path = None
        self._video_thread = None
        self._video_pause = threading.Event()  # set = running, clear = paused
        self._video_pause.set()
        self._preview_after_id = None

        # 加载配置 + 校验默认尺寸
        self._config_path = Path.home() / ".cym_cc_config.json"
        self._load_config()
        self._validate_size(self.width.get(), self.height.get(), silent=True)

        # 状态栏文本 (在 create_widgets 之前初始化, status bar 引用)
        self.status_var = tk.StringVar(value="Ready")

        # 创建UI
        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def set_window_icon(self):
        try:
            icon_path = "cym_icon.ico"
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "cym_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                return
            if resources is None or not hasattr(resources, "get"):
                return
            data = resources.get("cym_icon.ico")
            if not data:
                return
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".ico")
            tf.write(data)
            tf.flush()
            tf.close()
            self.root.iconbitmap(tf.name)
            self._icon_temp_path = tf.name
        except Exception as e:
            print(f"set icon failed: {e}")

    def _on_close(self):
        try:
            if self._icon_temp_path and os.path.exists(self._icon_temp_path):
                try:
                    os.unlink(self._icon_temp_path)
                except OSError:
                    pass
            self._icon_temp_path = None
        finally:
            self.root.destroy()
            self.root.quit()

    # --- 持久化配置 -------------------------------------------------

    def _load_config(self):
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for key, var in [
            ("width", self.width), ("height", self.height),
            ("image_folder", self.image_folder), ("output_file", self.output_file),
            ("video_file", self.video_file),
            ("scan_direction", self.scan_direction), ("scan_order", self.scan_order),
            ("slideshow_interval", self.slideshow_interval),
            ("video_frame_interval", self.video_frame_interval),
            ("brightness", self.brightness), ("contrast", self.contrast),
            ("rotation", self.rotation),
            ("invert_color", self.invert_color),
            ("horizontal_flip", self.horizontal_flip),
            ("vertical_flip", self.vertical_flip),
        ]:
            if key in data:
                try:
                    var.set(data[key])
                except (tk.TclError, ValueError):
                    pass

    def _save_config(self):
        try:
            data = {
                "width": self.width.get(), "height": self.height.get(),
                "image_folder": self.image_folder.get(),
                "output_file": self.output_file.get(),
                "video_file": self.video_file.get(),
                "scan_direction": self.scan_direction.get(),
                "scan_order": self.scan_order.get(),
                "slideshow_interval": self.slideshow_interval.get(),
                "video_frame_interval": self.video_frame_interval.get(),
                "brightness": self.brightness.get(),
                "contrast": self.contrast.get(),
                "rotation": self.rotation.get(),
                "invert_color": bool(self.invert_color.get()),
                "horizontal_flip": bool(self.horizontal_flip.get()),
                "vertical_flip": bool(self.vertical_flip.get()),
            }
            self._config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            print(f"save config failed: {e}")

    def _on_close(self):
        try:
            self._save_config()
            if self._icon_temp_path and os.path.exists(self._icon_temp_path):
                try:
                    os.unlink(self._icon_temp_path)
                except OSError:
                    pass
            self._icon_temp_path = None
        finally:
            self.root.destroy()
            self.root.quit()

    # --- 尺寸校验 / padding ----------------------------------------

    @staticmethod
    def _normalize_size(w, h):
        W = ((w + 7) // 8) * 8 if w > 0 else 8
        H = ((h + 7) // 8) * 8 if h > 0 else 8
        return W, H, (W != w or H != h)

    def _validate_size(self, w, h, silent=False):
        if not (1 <= w <= self._MAX_DIM and 1 <= h <= self._MAX_DIM):
            if not silent:
                messagebox.showerror("invalid size", f"W/H must be in [1, {self._MAX_DIM}]")
            return False
        W, H, padded = self._normalize_size(w, h)
        self.width.set(W)
        self.height.set(H)
        self._W = W
        self._H = H
        self._was_padded = padded
        if padded and not silent:
            messagebox.showinfo("size padded",
                                f"requested {w}x{h} is not a multiple of 8; padded to {W}x{H}")
        return True

    def _apply_size(self):
        try:
            w = int(self.width.get())
            h = int(self.height.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("invalid size", "W/H must be integers")
            return
        if self._validate_size(w, h):
            self.slideshow_canvas.config(width=self._W * 2, height=self._H * 2)
            if self.image_folder.get():
                self.refresh_preview()

    # --- GUI styling (modern ttk theme) ---

    def _init_style(self):
        """Apply a modern ttk theme: 'vista' on Windows (native look),
        'clam' as a clean fallback. Bigger fonts, generous padding,
        a touch of color on accent buttons."""
        style = ttk.Style(self.root)
        for theme in ("vista", "winnative", "clam", "alt", "default"):
            if theme in style.theme_names():
                try:
                    style.theme_use(theme)
                    break
                except tk.TclError:
                    continue
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(family=default_font.cget("family"), size=10)
            text_font = tkfont.nametofont("TkTextFont")
            text_font.configure(family=text_font.cget("family"), size=10)
        except Exception:
            pass
        style.configure("TFrame", padding=2)
        style.configure("TLabelFrame", padding=8)
        style.configure("TLabelFrame.Label", font=("TkDefaultFont", 10, "bold"))
        style.configure("TButton", padding=(10, 5))
        style.configure("Accent.TButton", padding=(12, 6), font=("TkDefaultFont", 10, "bold"))
        style.configure("TEntry", padding=4)
        style.configure("TCombobox", padding=4)
        style.configure("Horizontal.TProgressbar", thickness=8)
        style.configure("Status.TLabel", padding=(8, 4), foreground="#444444")

    def _init_status_bar(self):
        """Build a thin status bar at the bottom of the window.
        Updated via _update_status(text)."""
        self._status_frame = ttk.Frame(self.root, relief="sunken", padding=(8, 2))
        self._status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self._status_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(
            self._status_frame, textvariable=self.status_var,
            style="Status.TLabel", anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self._status_separator = ttk.Separator(self.root, orient="horizontal")
        self._status_separator.grid(row=2, column=0, sticky=(tk.W, tk.E))

    def _update_status(self, text, level="info"):
        """Update the status bar. level in ('info', 'warn', 'error')."""
        self.status_var.set(text)
        try:
            style = ttk.Style(self.root)
            color = {"info": "#444444", "warn": "#b35900", "error": "#cc0000"}.get(level, "#444444")
            style.configure("Status.TLabel", foreground=color)
        except Exception:
            pass
    def create_widgets(self):
        """Two-column layout: left = scrollable controls, right = preview/slideshow.

        Layout:
            row 0: header (title + subtitle)
            row 1: PanedWindow horizontal  -> left controls, right preview+slideshow
            row 2: status separator
            row 3: status bar
        """
        # --- Modern ttk theme + global styles ---
        self._init_style()

        # --- Top: header bar ---
        self._build_header()

        # --- Middle: PanedWindow (left controls, right preview) ---
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=8, pady=(0, 4))
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Left pane: scrollable controls
        self._build_left_pane(self.paned)
        # Right pane: preview + slideshow
        self._build_right_pane(self.paned)

        # --- Status bar (bottom) ---
        self._init_status_bar()

    def _build_header(self):
        """Top header: bold title + subtitle."""
        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=8, pady=(8, 0))
        header_frame.columnconfigure(0, weight=1)
        ttk.Label(
            header_frame, text="图像转字模工具  v2.0",
            font=("TkDefaultFont", 14, "bold")
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            header_frame,
            text="屏幕、视频、扫描参数可调 · 点击【开始转换】生成 C 字模",
            foreground="#666666"
        ).grid(row=1, column=0, sticky=tk.W, pady=(2, 0))

    def _build_left_pane(self, parent_paned):
        """Left pane: scrollable canvas with all control sections."""
        container = ttk.Frame(parent_paned)
        parent_paned.add(container, weight=2)

        canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e, c=canvas, iid=inner_id: c.itemconfig(iid, width=e.width))

        def _on_wheel(event, c=canvas):
            c.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_wheel)
        canvas.bind("<Button-4>", lambda e, c=canvas: c.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e, c=canvas: c.yview_scroll(1, "units"))

        self._add_file_section(inner)
        self._add_screen_section(inner)
        self._add_params_section(inner)
        self._add_control_buttons(inner)
        self._add_inspire_button(inner)

    def _build_right_pane(self, parent_paned):
        """Right pane: preview grid on top, slideshow on bottom."""
        container = ttk.Frame(parent_paned)
        parent_paned.add(container, weight=3)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=3)  # preview gets more
        container.rowconfigure(1, weight=2)  # slideshow

        preview_frame = ttk.LabelFrame(container, text="图像预览", padding="8")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 4))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(preview_frame, bg="white")
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_sb = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_sb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_sb = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_sb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.canvas.configure(yscrollcommand=v_sb.set, xscrollcommand=h_sb.set)

        slideshow_frame = ttk.LabelFrame(container, text="幻灯片播放", padding="8")
        slideshow_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(4, 0))
        slideshow_frame.columnconfigure(0, weight=1)
        slideshow_frame.rowconfigure(0, weight=1)
        self.slideshow_canvas = tk.Canvas(
            slideshow_frame, bg="black",
            width=max(self._W * 2, 256), height=max(self._H * 2, 128)
        )
        self.slideshow_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        ctrl = ttk.Frame(slideshow_frame)
        ctrl.grid(row=1, column=0, pady=(5, 0))
        self.play_button = ttk.Button(ctrl, text="播放", command=self.start_slideshow)
        self.play_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(ctrl, text="停止", command=self.stop_slideshow, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(ctrl, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT)

    def _add_file_section(self, parent):
        """File selection widgets."""
        frame = ttk.LabelFrame(parent, text="文件设置", padding="8")
        frame.pack(fill=tk.X, padx=4, pady=4)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="图像文件夹:").grid(row=0, column=0, sticky=tk.W, pady=2)
        row0 = ttk.Frame(frame); row0.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(5, 0))
        row0.columnconfigure(0, weight=1)
        ttk.Entry(row0, textvariable=self.image_folder).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(row0, text="浏览...", width=8, command=self.browse_folder).grid(row=0, column=1, padx=(4, 0))
        ttk.Label(frame, text="输出文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        row1 = ttk.Frame(frame); row1.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(5, 0))
        row1.columnconfigure(0, weight=1)
        ttk.Entry(row1, textvariable=self.output_file).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(row1, text="浏览...", width=8, command=self.browse_output).grid(row=0, column=1, padx=(4, 0))
        ttk.Label(frame, text="视频文件:").grid(row=2, column=0, sticky=tk.W, pady=2)
        row2 = ttk.Frame(frame); row2.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(5, 0))
        row2.columnconfigure(0, weight=1)
        ttk.Entry(row2, textvariable=self.video_file).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(row2, text="浏览...", width=8, command=self.browse_video).grid(row=0, column=1, padx=(4, 0))
        ttk.Label(frame, text="帧间隔:").grid(row=3, column=0, sticky=tk.W, pady=2)
        fi = ttk.Frame(frame); fi.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Entry(fi, textvariable=self.video_frame_interval, width=8).pack(side=tk.LEFT)
        ttk.Label(fi, text="帧").pack(side=tk.LEFT, padx=(4, 8))
        self.video_extract_btn = ttk.Button(fi, text="从视频生成图片", command=self.extract_frames_from_video)
        self.video_extract_btn.pack(side=tk.LEFT)
        self.video_info_label = ttk.Label(frame, text="(select a video to inspect)")
        self.video_info_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))
        self.video_progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate", maximum=100)
        self.video_progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(2, 0))
        self.video_progress.grid_remove()
        self.video_progress_label = ttk.Label(frame, text="")
        self.video_progress_label.grid(row=6, column=0, columnspan=3, sticky=tk.W)
        self.video_progress_label.grid_remove()
        pause_row = ttk.Frame(frame)
        pause_row.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
        self.video_pause_btn = ttk.Button(pause_row, text="pause", command=self._toggle_video_pause, state=tk.DISABLED, width=10)
        self.video_pause_btn.pack(side=tk.LEFT)

    def _add_screen_section(self, parent):
        """Screen size W, H inputs."""
        frame = ttk.LabelFrame(parent, text="屏幕尺寸 (8 的倍数; 上限 16384)", padding="8")
        frame.pack(fill=tk.X, padx=4, pady=4)
        frame.columnconfigure(1, weight=1)
        row = ttk.Frame(frame); row.pack(fill=tk.X)
        ttk.Label(row, text="宽 (W):").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.width, width=10).pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(row, text="高 (H):").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.height, width=10).pack(side=tk.LEFT, padx=(5, 15))
        ttk.Button(row, text="应用到图像处理", command=self._apply_size).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(frame, text="(非 8 倍会自动 pad; 改 C 端 oled/OLED.h 顶部 #define 同步硬件)",
                  foreground="#888888").pack(anchor=tk.W, pady=(4, 0))

    def _add_params_section(self, parent):
        """Brightness, contrast, invert, rotation, mirror, scan direction + order, slideshow interval."""
        frame = ttk.LabelFrame(parent, text="图像参数调节", padding="8")
        frame.pack(fill=tk.X, padx=4, pady=4)
        frame.columnconfigure(1, weight=1)

        r = ttk.Frame(frame); r.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        r.columnconfigure(0, weight=1)
        ttk.Label(r, text="亮度:").grid(row=0, column=0, sticky=tk.W)
        ttk.Scale(r, from_=-100, to=100, variable=self.brightness, orient=tk.HORIZONTAL, command=self.update_preview).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.brightness_label = ttk.Label(r, text="0", width=5)
        self.brightness_label.grid(row=0, column=2)

        r = ttk.Frame(frame); r.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        r.columnconfigure(0, weight=1)
        ttk.Label(r, text="对比度:").grid(row=0, column=0, sticky=tk.W)
        ttk.Scale(r, from_=0, to=3, variable=self.contrast, orient=tk.HORIZONTAL, command=self.update_preview).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.contrast_label = ttk.Label(r, text="1.0", width=5)
        self.contrast_label.grid(row=0, column=2)

        r = ttk.Frame(frame); r.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        ttk.Checkbutton(r, text="反色", variable=self.invert_color, command=self.update_preview).pack(side=tk.LEFT)
        for v, t in [("0", "0°"), ("90", "90°"), ("180", "180°"), ("270", "270°")]:
            ttk.Radiobutton(r, text=t, variable=self.rotation, value=v, command=self.update_preview).pack(side=tk.LEFT, padx=(8, 0))

        r = ttk.Frame(frame); r.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        ttk.Checkbutton(r, text="水平镜像", variable=self.horizontal_flip, command=self.update_preview).pack(side=tk.LEFT)
        ttk.Checkbutton(r, text="垂直镜像", variable=self.vertical_flip, command=self.update_preview).pack(side=tk.LEFT, padx=(8, 0))

        r = ttk.Frame(frame); r.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(6, 2))
        ttk.Label(r, text="扫描方向:").pack(side=tk.LEFT)
        ttk.Radiobutton(r, text="vertical", variable=self.scan_direction, value="vertical", command=self.update_preview).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(r, text="horizontal", variable=self.scan_direction, value="horizontal", command=self.update_preview).pack(side=tk.LEFT)

        r = ttk.Frame(frame); r.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(r, text="扫描顺序:").pack(side=tk.LEFT)
        order_grid = ttk.Frame(frame); order_grid.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        scan_orders = [
            ("L→R, T→B", "left_to_right_top_to_bottom"),
            ("T→B, L→R", "top_to_bottom_left_to_right"),
            ("R→L, T→B", "right_to_left_top_to_bottom"),
            ("T→B, R→L", "top_to_bottom_right_to_left"),
            ("B→T, L→R", "bottom_to_top_left_to_right"),
            ("L→R, B→T", "left_to_right_bottom_to_top"),
            ("R→L, B→T", "right_to_left_bottom_to_top"),
            ("B→T, R→L", "bottom_to_top_right_to_left"),
        ]
        for i, (label, value) in enumerate(scan_orders):
            rr, cc = divmod(i, 2)
            ttk.Radiobutton(order_grid, text=label, variable=self.scan_order, value=value, command=self.update_preview).grid(row=rr, column=cc, sticky=tk.W, padx=(0, 12))

        r = ttk.Frame(frame); r.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(6, 2))
        ttk.Label(r, text="幻灯片间隔 (ms):").pack(side=tk.LEFT)
        ttk.Entry(r, textvariable=self.slideshow_interval, width=10).pack(side=tk.LEFT, padx=(5, 0))

    def _add_control_buttons(self, parent):
        """Refresh / start conversion / exit buttons."""
        frame = ttk.LabelFrame(parent, text="操作", padding="8")
        frame.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(frame, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(frame, text="开始转换", command=self.convert_images, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(frame, text="退出", command=self.root.quit).pack(side=tk.LEFT)

    def _add_inspire_button(self, parent):
        """Inspire button (easter egg)."""
        ttk.Button(parent, text="激励", command=self.show_inspire_image).pack(anchor=tk.W, padx=4, pady=4)


    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder.set(folder)
            
    def browse_output(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C Files", "*.c"), ("All Files", "*.*")]
        )
        if file:
            self.output_file.set(file)
            
    def browse_video(self):
        # cv2.VideoCapture can read any container FFmpeg supports.
        file = filedialog.askopenfilename(
            filetypes=[
                ("All supported video", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv *.m4v "
                     "*.3gp *.ts *.m2ts *.mpg *.mpeg *.ogv *.vob *.rm *.rmvb *.asf"),
                ("All files", "*.*"),
            ]
        )
        if file:
            self.video_file.set(file)
            self._inspect_video(file)
            
    def _set_video_progress(self, pct, label):
        if pct is None:
            self.video_progress.configure(mode='indeterminate')
            self.video_progress.start(50)
        else:
            self.video_progress.configure(mode='determinate', value=pct * 100)
        self.video_progress_label.config(text=label)

    def _show_video_ui(self, show):
        if show:
            self.video_progress.grid()
            self.video_progress_label.grid()
        else:
            self.video_progress.grid_remove()
            self.video_progress_label.grid_remove()
            self.video_progress.stop()
            self.video_progress.configure(mode='determinate', value=0)
            self.video_progress_label.config(text='')

    def _toggle_video_pause(self):
        if self._video_pause.is_set():
            self._video_pause.clear()
            self.video_pause_btn.config(text='resume')
        else:
            self._video_pause.set()
            self.video_pause_btn.config(text='pause')

    def _video_busy(self, busy):
        btn = getattr(self, 'video_extract_btn', None)
        if btn is not None:
            btn.config(state=tk.DISABLED if busy else tk.NORMAL)
        self.video_pause_btn.config(state=tk.NORMAL if busy else tk.DISABLED)
        if not busy:
            self.video_pause_btn.config(text='pause')
            self._video_pause.set()

    def _inspect_video(self, path):
        cap = cv2.VideoCapture(path)
        try:
            if not cap.isOpened():
                self.video_info_label.config(text='(cannot open)')
                return
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            fourcc = ''.join(chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)) or '????'
            fps = cap.get(cv2.CAP_PROP_FPS)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_info_label.config(
                text=f'codec: {fourcc} | {fps:.1f} fps | {w}x{h} | {n} frames'
            )
        finally:
            cap.release()


    def extract_frames_from_video(self):
        video_path = self.video_file.get()
        output_folder = self.image_folder.get()
        frame_interval = self.video_frame_interval.get()
        if not video_path:
            messagebox.showwarning("warning", "please select a video file")
            return
        if not output_folder:
            messagebox.showwarning("warning", "please select an output folder")
            return
        if frame_interval <= 0:
            messagebox.showwarning("warning", "frame interval must be > 0")
            return
        if self._video_thread is not None and self._video_thread.is_alive():
            messagebox.showinfo("info", "previous extraction still in progress")
            return

        self._update_status(f"extracting from {os.path.basename(video_path)}...", "info")

        def _worker():
            cap = None
            err = None
            saved_count = 0
            corrupt = 0
            total = 0
            try:
                os.makedirs(output_folder, exist_ok=True)
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    err = RuntimeError("cannot open video file")
                    return
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.root.after(0, lambda t=total: self._set_video_progress(
                    None if t <= 0 else 0.0,
                    f"frame 0 / {t}" if t > 0 else "frame 0 / ?"))

                frame_count = 0
                last_report = 0
                while True:
                    if not self._video_pause.is_set():
                        self._video_pause.wait(timeout=0.1)
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if frame is None or frame.size == 0:
                        corrupt += 1
                        frame_count += 1
                        continue
                    if frame_count % frame_interval == 0:
                        try:
                            resized = cv2.resize(frame, (self._W, self._H))
                            cv2.imwrite(os.path.join(output_folder, f"frame_{saved_count:04d}.png"), resized)
                            saved_count += 1
                        except Exception:
                            corrupt += 1
                    frame_count += 1
                    if frame_count - last_report >= max(50, total // 50 if total > 0 else 100):
                        last_report = frame_count
                        pct = (frame_count / total) if total > 0 else None
                        self.root.after(0, lambda p=pct, fc=frame_count, t=total, sv=saved_count:
                            self._set_video_progress(p,
                                f"frame {fc}/{t} saved {sv}" if t > 0 else f"frame {fc} saved {sv}"))
            except Exception as e:
                err = e
            finally:
                if cap is not None:
                    cap.release()

            def _done():
                self._show_video_ui(False)
                self._video_busy(False)
                if err is not None:
                    messagebox.showerror("error", f"video extract failed: {err}")
                else:
                    msg = f"extracted {saved_count} frames to {output_folder}"
                    if corrupt:
                        msg += f"  ({corrupt} corrupt frames skipped)"
                    messagebox.showinfo("done", msg)
                    self.refresh_preview()
            self.root.after(0, _done)

        self._video_busy(True)
        self._show_video_ui(True)
        self._video_pause.set()
        self.video_pause_btn.config(text="pause")
        self._video_thread = threading.Thread(target=_worker, daemon=True)
        self._video_thread.start()
    def apply_brightness_contrast(self, image):
        # 应用亮度和对比度调整
        brightness = self.brightness.get()
        contrast = self.contrast.get()
        
        # 转换为浮点型进行计算
        img = image.astype(np.float32)
        
        # 应用对比度和亮度
        img = img * contrast + brightness
        
        # 截断到有效范围
        img = np.clip(img, 0, 255)
        
        # 转换回uint8
        return img.astype(np.uint8)
        
    def convert_to_bitmap(self, image):
        """Resize to (self._W, self._H), apply brightness/contrast, optional rotation/
        mirror, invert, then threshold to binary."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        adjusted = self.apply_brightness_contrast(gray)
        if self.rotation.get() == "90":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation.get() == "180":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_180)
        elif self.rotation.get() == "270":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if self.horizontal_flip.get():
            adjusted = cv2.flip(adjusted, 1)
        if self.vertical_flip.get():
            adjusted = cv2.flip(adjusted, 0)
        adjusted = cv2.resize(adjusted, (self._W, self._H), interpolation=cv2.INTER_NEAREST)
        if self.invert_color.get():
            adjusted = 255 - adjusted
        _, binary = cv2.threshold(adjusted, 127, 255, cv2.THRESH_BINARY)
        return binary
    # Bit weights for packing 8 pixels into a byte (MSB first).
    # For right-to-left horizontal scan orders the original code reads pixels
    # right-to-left with LSB weights; reading them left-to-right with these MSB
    # weights produces the same byte (the rightmost pixel ends up weighted 1 = bit 0).
    _WEIGHTS_MSB = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint16)

    @staticmethod
    def _make_iter(direction, order, W, H):
        """Return a list of (orient, a, b) tuples for the given scan params.
        "V" with (a, b) = (row_start, col) -> byte covers 8 vertical pixels of column b.
        "H" with (a, b) = (row, col_start) -> byte covers 8 horizontal pixels of row a.
        Iteration order matches the original code; the bottom_to_top horizontal col-major
        quirk (rows 63, 55, ..., 7 instead of 56, 48, ..., 0) is preserved for
        backwards compatibility with previously generated C arrays."
        """
        if direction == "vertical":
            if order in ("left_to_right_top_to_bottom", "top_to_bottom_left_to_right"):
                pages, cols = range(0, H, 8), range(W)
            elif order in ("right_to_left_top_to_bottom", "top_to_bottom_right_to_left"):
                pages, cols = range(0, H, 8), range(W - 1, -1, -1)
            elif order in ("bottom_to_top_left_to_right", "left_to_right_bottom_to_top"):
                pages, cols = range(H - 8, -1, -8), range(W)
            else:  # right_to_left_bottom_to_top, bottom_to_top_right_to_left
                pages, cols = range(H - 8, -1, -8), range(W - 1, -1, -1)
            return [("V", p, c) for p in pages for c in cols]
        # horizontal
        if order == "left_to_right_top_to_bottom":
            return [("H", r, c) for r in range(H) for c in range(0, W, 8)]
        if order == "top_to_bottom_left_to_right":
            return [("V", r, c) for c in range(W) for r in range(0, H, 8)]
        if order == "right_to_left_top_to_bottom":
            return [("H", r, c) for r in range(H) for c in range(W - 8, -1, -8)]
        if order == "bottom_to_top_left_to_right":
            return [("V", r, c) for c in range(W) for r in range(H - 1, -1, -8)]
        if order == "left_to_right_bottom_to_top":
            return [("H", r, c) for r in range(H - 1, -1, -1) for c in range(0, W, 8)]
        if order == "right_to_left_bottom_to_top":
            return [("H", r, c) for r in range(H - 1, -1, -1) for c in range(W - 8, -1, -8)]
        if order == "top_to_bottom_right_to_left":
            return [("V", r, c) for c in range(W - 1, -1, -1) for r in range(0, H, 8)]
        # bottom_to_top_right_to_left
        return [("V", r, c) for c in range(W - 1, -1, -1) for r in range(H - 1, -1, -8)]

    @staticmethod
    def _pack_byte(is_black, orient, a, b, weights, W, H):
        """Pack 8 pixels into a byte. Slices clipped at W/H edges;
        out-of-bounds pixels are treated as not-black.
        """
        if orient == "V":
            bits = 0
            for k in range(8):
                if a + k < H and is_black[a + k, b]:
                    bits |= weights[k]
        else:
            bits = 0
            for k in range(8):
                if b + k < W and is_black[a, b + k]:
                    bits |= weights[k]
        return bits
    def image_to_font_data(self, image):
        """Convert a binary image of size (self._H, self._W) to a
        (self._W * self._H / 8)-byte OLED font matrix.
        See _make_iter for the layout mapping.
        """
        is_black = (self.convert_to_bitmap(image) == 0)
        weights = self._WEIGHTS_MSB
        W, H = self._W, self._H
        plan = self._make_iter(self.scan_direction.get(), self.scan_order.get(), W, H)
        return [self._pack_byte(is_black, orient, a, b, weights, W, H) for orient, a, b in plan]
    def update_preview(self, event=None):
        # Immediate parameter label update (no debounce)
        self.brightness_label.config(text=f"{self.brightness.get():.0f}")
        self.contrast_label.config(text=f"{self.contrast.get():.2f}")
        # Debounce: slider drag fires update_preview at high frequency;
        # delay the expensive preview rebuild by 150ms.
        if self._preview_after_id is not None:
            try:
                self.root.after_cancel(self._preview_after_id)
            except Exception:
                pass
        self._preview_after_id = self.root.after(150, self._do_refresh_preview)

    def _do_refresh_preview(self):
        self._preview_after_id = None
        self.refresh_preview()
    def refresh_preview(self):
        folder = self.image_folder.get()
        if not folder:
            messagebox.showwarning("警告", "请先选择图像文件夹")
            return
            
        # 获取文件夹中的图片
        image_files = glob.glob(os.path.join(folder, "*.png")) + \
                     glob.glob(os.path.join(folder, "*.jpg")) + \
                     glob.glob(os.path.join(folder, "*.jpeg")) + \
                     glob.glob(os.path.join(folder, "*.bmp"))
                     
        if not image_files:
            messagebox.showwarning("警告", "所选文件夹中没有找到图像文件")
            return
            
        # 显示所有图片的预览
        self.show_all_images_preview(image_files)
        
        # 更新幻灯片
        self.update_slideshow(image_files)
            
    def show_all_images_preview(self, image_files):
        # 清除之前的预览
        self.canvas.delete("all")
        
        # 创建一个Frame来容纳所有预览图像
        frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=frame, anchor="nw")
        
        # 显示所有图片
        images_per_row = 4
        preview_size = (self._W, self._H)
        
        self.preview_images = []
        for i, img_path in enumerate(image_files[:16]):  # 限制最多显示16张图片
            try:
                # 读取图像
                image = cv2.imread(img_path)
                if image is None:
                    continue
                    
                # 检查图像尺寸
                h, w = image.shape[:2]
                if h != 64 or w != 128:
                    continue
                    
                # 处理图像
                processed = self.convert_to_bitmap(image)
                
                # 转换为RGB格式以便在tkinter中显示
                rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                
                # 转换为tkinter可用格式
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(rgb_image)
                tk_image = ImageTk.PhotoImage(pil_image)
                self.preview_images.append(tk_image)  # 保持引用防止被垃圾回收
                
                # 计算位置
                row = i // images_per_row
                col = i % images_per_row
                
                # 创建图像标签
                label_frame = tk.Frame(frame, relief=tk.RAISED, bd=2)
                label_frame.grid(row=row*2, column=col, padx=5, pady=5)
                
                # 显示图像
                img_label = tk.Label(label_frame, image=tk_image, bg="white")
                img_label.pack()
                
                # 显示文件名
                filename = os.path.basename(img_path)
                name_label = tk.Label(label_frame, text=filename, bg="white")
                name_label.pack()
                
            except Exception as e:
                print(f"无法加载图像 {img_path}: {e}")
        
        # 更新滚动区域
        frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
    def update_slideshow(self, image_files):
        # 更新幻灯片图像列表
        self.slideshow_images = []
        for img_path in image_files:
            try:
                # 读取图像
                image = cv2.imread(img_path)
                if image is None:
                    continue
                    
                # 检查图像尺寸
                h, w = image.shape[:2]
                if h != 64 or w != 128:
                    continue
                    
                # 处理图像
                processed = self.convert_to_bitmap(image)
                
                # 转换为RGB格式以便在tkinter中显示
                rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                
                # 转换为tkinter可用格式，放大到256x128
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(rgb_image)
                pil_image = pil_image.resize((self._W * 2, self._H * 2), Image.LANCZOS)
                tk_image = ImageTk.PhotoImage(pil_image)
                self.slideshow_images.append(tk_image)  # 保持引用防止被垃圾回收
            except Exception as e:
                print(f"无法加载幻灯片图像 {img_path}: {e}")
        
        # 显示第一张图像
        self.slideshow_index = 0
        if self.slideshow_images:
            self.slideshow_canvas.delete("all")
            self.slideshow_canvas.create_image(
                self.slideshow_canvas.winfo_width() // 2,
                self.slideshow_canvas.winfo_height() // 2,
                anchor=tk.CENTER,
                image=self.slideshow_images[0]
            )
        
    def show_processed_image(self):
        if not hasattr(self, 'preview_image') or self.preview_image is None:
            return
            
        # 处理图像
        processed = self.convert_to_bitmap(self.preview_image)
        
        # 转换为RGB格式以便在tkinter中显示
        rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        
        # 转换为tkinter可用格式
        from PIL import Image, ImageTk
        pil_image = Image.fromarray(rgb_image)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        
        # 在canvas中显示
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
    def start_slideshow(self):
        if not self.slideshow_images:
            messagebox.showwarning("警告", "没有可播放的图像")
            return
            
        self.slideshow_running = True
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.slideshow()
        
    def stop_slideshow(self):
        self.slideshow_running = False
        if self.slideshow_job:
            self.slideshow_canvas.after_cancel(self.slideshow_job)
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def slideshow(self):
        if not self.slideshow_running:
            return
            
        if self.slideshow_images:
            # 显示当前图像
            self.slideshow_canvas.delete("all")
            self.slideshow_canvas.create_image(
                self.slideshow_canvas.winfo_width() // 2,
                self.slideshow_canvas.winfo_height() // 2,
                anchor=tk.CENTER,
                image=self.slideshow_images[self.slideshow_index]
            )
            
            # 更新索引
            self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_images)
            
        # 设置下次更新
        self.slideshow_job = self.slideshow_canvas.after(self.slideshow_interval.get(), self.slideshow)
        
    def _list_valid_images(self, folder):
        """Return all readable images whose pixel dimensions match (self._H, self._W)."""
        candidates = []
        for ext in ("png", "jpg", "jpeg", "bmp"):
            candidates.extend(glob.glob(os.path.join(folder, f"*.{ext}")))
        candidates.sort()
        valid = []
        for path in candidates:
            image = cv2.imread(path)
            if image is None:
                continue
            h, w = image.shape[:2]
            if h != self._H or w != self._W:
                continue
            valid.append(path)
        return valid
    @staticmethod
    def _format_hex_array(font_data, indent=4):
        """Format a font_data byte list as a C array literal (16 bytes per line)."""
        pad = " " * indent
        lines = []
        for j in range(0, len(font_data), 16):
            chunk = font_data[j:j + 16]
            lines.append(pad + ", ".join(f"0x{b:02X}" for b in chunk))
        return "{\n" + ",\n".join(lines) + "\n}"

    def convert_images(self):
        folder = self.image_folder.get()
        output = self.output_file.get()
        if not folder:
            messagebox.showwarning("warning", "please select an image folder")
            return
        if not output:
            messagebox.showwarning("warning", "please select an output file")
            return

        image_files = self._list_valid_images(folder)
        if not image_files:
            messagebox.showwarning("warning", f"no {self._W}x{self._H} images found in folder")
            return

        self._update_status(f"converting {len(image_files)} image(s) to {self._W}x{self._H} C array...", "info")
        try:
            slideshow_interval = self.slideshow_interval.get()
            W, H = self._W, self._H
            with open(output, "w", encoding="utf-8") as f:
                f.write(f"// OLED font matrix data - {W}x{H}")
                if self._was_padded:
                    f.write(f"  (NOTE: requested WxH was padded to {W}x{H})")
                f.write("\n")
                f.write("#include <stdint.h>\n\n")
                for i, img_path in enumerate(image_files):
                    image = cv2.imread(img_path)
                    if image is None:
                        continue
                    font_data = self.image_to_font_data(image)
                    array_name = f"IMG_DATA{i + 1}"
                    f.write(f"const uint8_t {array_name}[] = {self._format_hex_array(font_data)};\n\n")

                n = len(image_files)
                f.write(f"// total: {n} image(s)\n")
                f.write(f"// OLED_ShowImage calls below use ({W}, {H})\n")
                f.write("void gif(void) {\n")
                for i in range(n):
                    f.write(f"    OLED_ShowImage(0,0,{W},{H},IMG_DATA{i + 1});"
                            f"OLED_Update();delay_1ms({slideshow_interval});OLED_Clear();\n")
                f.write("}\n")

            header_file = output[:-2] + ".h" if output.endswith(".c") else output + ".h"
            with open(header_file, "w", encoding="utf-8") as f:
                header_filename = os.path.basename(header_file)
                header_name_upper = "".join(c.upper() if c.isalnum() else "_" for c in header_filename)
                protect_macro = f"__{header_name_upper}"
                f.write(f"#ifndef {protect_macro}\n#define {protect_macro}\n\n")
                f.write("#include <stdint.h>\n\n")
                for i in range(len(image_files)):
                    f.write(f"extern const uint8_t IMG_DATA{i + 1}[];\n")
                f.write("\nextern void gif(void);\n")
                f.write(f"\n#endif // {protect_macro}\n")

            self._update_status(f"converted {len(image_files)} image(s) -> {output}", "info")
            messagebox.showinfo("done", f"converted {len(image_files)} image(s)\n{output}\n{header_file}")
        except Exception as e:
            self._update_status(f"conversion failed: {e}", "error")
            messagebox.showerror("error", f"conversion failed: {e}")
    def show_inspire_image(self):
        # 加载并显示激励图片，优先从内嵌 resources 加载，回退到磁盘文件
        img_path = "jili.jpg"  # 默认磁盘文件名
        from PIL import Image, ImageTk

        try:
            pil_image = None

            # 先尝试磁盘路径
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)

            # 如果磁盘没有，尝试从 resources 中读取
            if pil_image is None and resources is not None and hasattr(resources, 'get'):
                data = resources.get('jili.jpg') or resources.get('jili.png')
                if data:
                    pil_image = Image.open(io.BytesIO(data))

            if pil_image is None:
                raise FileNotFoundError('激励图片未找到（磁盘或内嵌资源中均无）')

            # 转换为tkinter可用格式
            tk_image = ImageTk.PhotoImage(pil_image)

            # 创建新的窗口
            inspire_window = tk.Toplevel(self.root)
            inspire_window.title("谢谢您的激励！")
            inspire_window.geometry(f"{pil_image.width}x{pil_image.height}")  # 设置窗口大小为图片尺寸

            # 在新窗口中显示图像
            canvas = tk.Canvas(inspire_window, bg="white", width=pil_image.width, height=pil_image.height)
            canvas.pack(fill=tk.BOTH, expand=True)

            # 显示图像
            canvas.create_image(
                pil_image.width // 2,
                pil_image.height // 2,
                anchor=tk.CENTER,
                image=tk_image
            )

            # 保持引用防止被垃圾回收
            canvas.image = tk_image

            # 禁止调整窗口大小
            inspire_window.resizable(False)

        except Exception as e:
            messagebox.showwarning("警告", f"无法加载激励图片: {e}")

def main():
    root = tk.Tk()
    app = ImageToFontConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()