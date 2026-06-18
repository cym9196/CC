# Changelog

## 优化 (2026-06-19)

### CC.py — 主程序

* **`image_to_font_data` 8 路去重**（行为完全保持，112 条回归测试全过）：
  原来 8 个 `for/if/elif` 块（`vertical/horizontal` × 8 个 `scan_order`）共约 200 行。
  现已替换为一张 16 项的 `_FONT_ITER` 派发表 + 1 个 `_pack_byte` 辅助函数，
  整个函数 + 派发表约 70 行，可读性大幅提升，且无 1.0–1.2× 加速。

* **`convert_images` 修 3 个隐藏 bug**：
  1. 之前不管目录里有几张图，`.h` 文件总是写 25 个 `extern const uint8_t IMG_DATAxx[];`，
     在 `len(image_files) < 25` 时会引入未定义引用导致链接失败；
     现在只写实际生成的 `IMG_DATA1..N`。
  2. 之前 `image_files` 会把尺寸不对的图片也囊括进来，而转换循环又用 `continue` 跳过，
     导致 `gif()` 里的 `for i in range(len(image_files))` 引用了不存在的符号；
     现在用 `_list_valid_images` 一次性过滤掉非 128×64 或无法读取的图。
  3. `_format_hex_array` 把原来手工写的 16 字节换行抽成辅助函数。

* **`extract_frames_from_video` 改为后台线程**：
  之前在 UI 线程里逐帧 `cv2.read` + `cv2.imwrite`，视频稍长就完全卡死。
  现在用 `threading.Thread(daemon=True)` 在后台跑，
  通过 `self.root.after(0, ...)` 把完成消息和预览刷新投回主线程。
  同时加了“上一次抽帧还没结束”的去重检查。

* **`update_preview` 加 150 ms 防抖**：
  拖动亮度/对比度滑块时，原代码每个 tick 都会重建整个预览网格和幻灯片帧列表，
  体感卡顿。现在只更新参数文字标签，图片重建延迟 150 ms。

* **`set_window_icon` 临时文件不再泄漏**：
  原代码 `NamedTemporaryFile(delete=False)` 后只写注释“程序退出后由系统清理”，
  实际上会一直在 `%TEMP%` 里残留 `tmpXXXXXX.ico`。
  现在把路径记到 `self._icon_temp_path`，绑定 `WM_DELETE_WINDOW` 协议，
  关闭窗口时显式 `os.unlink`。

* **`show_inspire_image`** 加 `<Destroy>` 绑定清理对图片的引用。

* 顶部 import 顺序按 `stdlib → third-party` 整理。

### build.py — 打包脚本

* 资源改用 `bytes` 字面量嵌入（`repr()` of `bytes`），**resources.py 从 342 KB 降到 265 KB**（−22%），
  运行期也不再需要 `base64.b64decode`。
* 加 UPX 探测：找不到 UPX 时打 `WARNING` 而不是让 PyInstaller 默默跳过。
* 加 `--onedir` 选项：单文件模式（默认）启动慢、临时解压吃 IO，
  `onedir` 模式启动快、便于热更新。
* `excludes` 列表里预先剔除 `matplotlib / scipy / pandas / PyQt* / IPython / pytest / librosa / sklearn / pydoc / doctest` 等
  绝对不会用到的重模块，PyInstaller 体积能进一步缩小。
* 用 `logging` 替代 `print`，加 `argparse` 子命令，`create_resources_file` 还会检查内容是否变化，
  没变就不重写（避免触发不必要的 PyInstaller rebuild）。

### oled/ — 库代码

* `OLED.h` 顶部新增 `#define OLED_WIDTH 128` / `#define OLED_HEIGHT 64` / `#define OLED_PAGES ((OLED_HEIGHT+7)/8)`，
  全部 `#ifndef` 包裹以便用户在编译时覆盖。
* `OLED.c` 把 `OLED_DisplayBuf[8][128]` 改成 `OLED_DisplayBuf[OLED_PAGES][OLED_WIDTH]`，
  全部 `for (j = 0; j < 8; j++)` / `for (i = 0; i < 128; i++)` 改成对应的 `OLED_PAGES` / `OLED_WIDTH`，
  `OLED_WriteData` 的长度参数同步更新。函数签名完全不变。**SSD1306 的 I2C 命令序列保持原样**——
  如果用户换 SSD1322 / SH1106 等需要自己改 `OLED_Init` 里的命令序列。
* `cym_icon.ico` 已被 `resources.py` 嵌入，不再需要随包分发。

### 新增测试脚本

* `verify_original.py`：跨 7 张合成图 × 16 个 `(direction, order)` 组合 = 112 条用例，
  验证 `image_to_font_data` 与重构前行为字节级一致。
* `test_convert.py`：功能测试 — 空目录报警、过滤掉非 128×64 图、
  生成正确的 `.c`/`.h`、头文件不再有 25 个占位声明。
* `bench.py`：微基准。

---

## 自定义尺寸 + 多格式视频 (2026-06-19, 修订版)

### CC.py — 屏幕尺寸参数化 (W、H 任意, 上限 16384)

* **GUI** 在 `文件设置` 之后新增 `屏幕尺寸` LabelFrame：`宽 (W)` / `高 (H)` 两个 IntVar Entry + `应用到图像处理` 按钮 + 一行 hint。
* **`_MAX_DIM = 16384`** 硬上限（即"16K 屏幕"字面含义）。W/H 校验由 `_validate_size(w, h, silent=False)` 统一处理。
* **`_normalize_size(w, h)`** 把任意 W/H 向上 round 到 8 的倍数；非 8 倍输入会被 pad 并通过 `messagebox.showinfo` 告知一次。
  生成 C 代码首行会带 `// OLED font matrix data - WxH  (NOTE: requested WxH was padded to WxH)` 注释，方便回溯。
* **`_FONT_ITER` 静态 16 项表** 替换为 **动态 `_make_iter(direction, order, W, H)`**，由 (W, H) 推导每次的 byte 迭代顺序：
  - 保留原 `bottom_to_top` col-major 的 boundary quirk（行 63, 55, ..., 7 而不是 56, 48, ..., 0）—— 已在 112 条原始测试里固化，不动。
  - 各种 size × 16 order × 2 image 共 320 条新行为测试 (`verify_custom_size.py`) 全过。
* **滑动条/预览/幻灯片/生成的 C 代码** 全部用 `self._W` / `self._H` 动态计算。
* `convert_to_bitmap`、`_list_valid_images`、`show_all_images_preview`、`update_slideshow`、`slideshow_canvas` 都跟着改。
* `convert_images` 输出的 C 代码里 `OLED_ShowImage(0,0,W,H,IMG_DATA1)` 跟随当前 W/H 动态生成。

### CC.py — 视频多格式 + 进度条 + 暂停/恢复

* `browse_video` 文件对话框 filter 扩展到 19 种容器（mp4/avi/mov/mkv/webm/flv/wmv/m4v/3gp/ts/m2ts/mpg/mpeg/ogv/vob/rm/rmvb/asf），`cv2.VideoCapture` 实际能读所有 FFmpeg 支持的格式。
* 选中视频后自动调 `_inspect_video` 显示 `codec: h264 | 30.0 fps | 1920x1080 | 1234 frames`。
* **进度条** `ttk.Progressbar` 抽帧时实时更新（`frame X / Y  saved N`），抽完自动隐藏。
* **暂停 / 恢复** 按钮：worker 在每帧循环里 `self._video_pause.wait()`；按钮文字在 "pause" / "resume" 之间切换。
* **损坏帧处理**：`ret, frame = cap.read()` 后若 `frame is None or frame.size == 0`，计入 `corrupt` 计数并跳过；最终 messagebox 报告 `extracted N frames ... (M corrupt frames skipped)`。
* 防止抽帧按钮重入：抽帧进行中按钮置 disabled，完成后恢复。

### CC.py — 配置持久化

* 顶部增 `import json` / `from pathlib import Path`。
* `self._config_path = Path.home() / ".cym_cc_config.json"`。
* `_load_config()` 在 `__init__` 期间（`create_widgets` 之前）调用，恢复上次保存的 14 个参数（W/H、各路径、scan_direction/scan_order、brightness/contrast/rotation/invert/flip、slideshow/video_frame interval）。
* `_save_config()` 在 `_on_close` 之前调用，失败仅 `print` 不弹窗。
* 配置文件存到用户目录，不污染项目目录，跨 Windows / macOS / Linux。

### oled/ — C 驱动 #define 参数化

* `OLED.h` 顶部新增：
  ```c
  #ifndef OLED_WIDTH
  #define OLED_WIDTH  128
  #endif
  #ifndef OLED_HEIGHT
  #define OLED_HEIGHT 64
  #endif
  #define OLED_PAGES  ((OLED_HEIGHT + 7) / 8)
  ```
* `OLED.c` 把 `uint8_t OLED_DisplayBuf[8][128];` 改成 `uint8_t OLED_DisplayBuf[OLED_PAGES][OLED_WIDTH];`，
  全部 `for (j = 0; j < 8; j++)` / `for (i = 0; i < 128; i++)` 改成对应的 `OLED_PAGES` / `OLED_WIDTH`，
  `OLED_WriteData(OLED_DisplayBuf[j], 128)` 的长度参数同步。函数签名完全不变。
* 用户改 `OLED_WIDTH` / `OLED_HEIGHT` 后整库重新编译即可支持新尺寸。**SSD1306 的 I2C 命令序列保持原样**——
  如果用户换 SSD1322 / SH1106 等需要自己改 `OLED_Init` 里的命令序列。
* 16K×16K 满配时 `OLED_DisplayBuf` 是 256 MB，**用户的 C 端 RAM 必须能容纳**——README 提示。

### 测试

* `verify_original.py` — 112 条 128×64 回归测试（保持，全过）。
* `verify_custom_size.py` — 5 尺寸 × 2 方向 × 8 order × 2 image = 160 条新行为测试（全过）。
* `test_convert.py` — 功能测试，加了 96×16、100×30 (padded to 104×32) 等用例。
* `bench.py` — 微基准，覆盖 4 个尺寸 × 4 个 order 组合。

### 升级步骤

```bash
cd CC字模
python verify_original.py        # 期望: Total: 112 cases, Mismatches: 0
python verify_custom_size.py     # 期望: Total: 160 cases, Fails: 0
python test_convert.py           # 期望: All convert_images tests passed.
python bench.py                  # 期望: 所有 ms/iter 都在合理范围
```

按需编辑 `oled/OLED.h` 顶部的 `#define OLED_WIDTH` / `#define OLED_HEIGHT` 同步硬件尺寸，
再 `python build.py` 重新打包。Python 工具的 W/H 必须在 GUI 里设成一致值。

### 不向后兼容的地方

* `convert_to_bitmap` 现在按用户当前 W/H 缩放（之前硬 128×64），如果历史项目里的图都是 128×64 那没影响。
* `convert_images` 生成的 `.c` 文件首行从 `// font matrix data` 变成 `// OLED font matrix data - WxH`。
* 16K×16K 满配 = 256 MB 帧缓冲，需用户硬件/C 编译器扛得住。
