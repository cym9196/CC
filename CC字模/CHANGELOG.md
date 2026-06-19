# Changelog

## v0.4 (rev2) - 三 tab Notebook 布局 (2026-06-19)

之前的 v0.3 两栏布局把 header / file / screen / params / preview / controls 全部塞在 main_frame 的不同 row 里，
960x800 默认窗口下预览和幻灯片都挤到屏幕外。
v0.3 改成 ttk.PanedWindow 水平两栏后，左侧 controls 区域里的子项 (文件设置/屏幕尺寸/图像参数调节/控制按钮) 太多，
scrollable frame 也不够好用。v0.4 直接换成 ttk.Notebook 三 tab 布局：

### 布局 (v0.4)

```
+--------------------------------------------------------------------+
|  图像转字模工具  v2.0                                W=128 H=64   |  <- row 0: header
+--------------------------------------------------------------------+
|  [屏幕] [参数] [操作]  Notebook  |  [图像预览]      (weight=3)      |  <- row 1: paned
|  (left pane, 360px)              |  [幻灯片播放]    (weight=2)      |
+--------------------------------------------------------------------+
|  Ready | W=128 H=64 | v2.0 GUI | ...                             |  <- row 2: status
+--------------------------------------------------------------------+
```

### 改动

* **create_widgets 重写**：拆分出 _build_header / _build_left_pane / _build_right_pane / _init_status_bar。
* **_build_left_pane** 用 ttk.Notebook，3 个 tab：
  * **屏幕**：宽 W / 高 H + 应用到图像处理 按钮 + 提示标签 (8 倍 padding / C 端 #define)
  * **参数**：亮度/对比度滑块 + 反色 + 旋转 (0/90/180/270) + 水平/垂直镜像 + 扫描方向 (vertical/horizontal) + 8 种扫描顺序 + 幻灯片间隔
  * **操作**：刷新预览 / 开始转换 / 退出 3 个大按钮 + 视频抽帧 (文件 + 帧间隔 + 进度 + 暂停) + 激励按钮
* **_build_right_pane**：preview canvas (weight=3) + slideshow canvas (weight=2)，永远可见。
* **sash 起始位置**固定 360 px (self.paned.sashpos(0, 360) 在 __init__ 里 create_widgets() 之后调)。
* **预览画布背景** #fafafa，**幻灯片画布背景** #0a0a0a，对比明显。
* **占位提示文字**:
  * 预览: 选择一个图像文件夹后, 点【刷新预览】查看预览 或点【开始转换】生成 C 字模数据
  * 幻灯片: 幻灯片预览 (need images)
* **状态栏 row 修正**: 之前 _init_status_bar 用 row=1 跟 paned 冲突；现在用 row=2，且去掉了旧的 separator line。
* **默认窗口尺寸** 1400x900。

### 删除

* _build_toolbar（v0.4 不再使用 toolbar；文件/视频输入移到 操作 tab 里）。
* 旧的 __init__ 里一坨 LabelFrame 拼接代码。

### 测试

* verify_original.py: **112/112 通过**
* verify_custom_size.py: **160/160 通过**
* test_convert.py: **全部通过**

### EXE

* PyInstaller 重新打包：CC字模/dist/CC.exe (~79 MB) -> 复制到 CC.exe。
* GitHub Release: **v0.4**。
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

## I2C 控制器适配 (2026-06-19)

### `oled/` — 适配更多 OLED 控制器

之前 `OLED.c` 把 SSD1306 的 I2C 协议和 init 序列全部硬编码。第三方控制器的用户 (SH1106 1.3" 模块 / 不同 I2C 地址的 SSD1306 模块 / SSD1322 / SSD1351 / ILI9341 等) 改起来很麻烦。改成纯宏 + 单独 init 序列文件。

* **`OLED.h` 顶部新增 6 个宏**：
  ```c
  #ifndef OLED_I2C_ADDR
  #define OLED_I2C_ADDR  0x78   /* SSD1306 默认; SH1106 用 0x7A */
  #endif
  #ifndef OLED_I2C_CMD
  #define OLED_I2C_CMD   0x00   /* 控制字节: 命令流 */
  #endif
  #ifndef OLED_I2C_DATA
  #define OLED_I2C_DATA  0x40   /* 控制字节: 数据流 */
  #endif
  #ifndef OLED_CONTROLLER
  #define OLED_CONTROLLER  OLED_CTRL_SSD1306
  #endif
  #define OLED_CTRL_SSD1306  0
  #define OLED_CTRL_SH1106   1
  #define OLED_CTRL_USER     2  /* 用你自己的 init 序列 */
  ```
  全部 `#ifndef` 包裹，编译期可覆盖。

* **`OLED_Controller.h` (新文件)**：按 `OLED_CONTROLLER` 编译期切换 init 序列。预置 `SSD1306` 和 `SH1106` 两种 (后者对 charge pump / precharge / vcomh 做了 SH1106 偏好的微调)。其它控制器 (SSD1322 / SSD1351 / ILI9341 等) 选 `OLED_CTRL_USER` 并在 include 之前 `#define OLED_INIT_USER() { ...你的 init 命令... }` 即可。

* **`OLED.c` 改动**：
  - `OLED_WriteCommand` / `OLED_WriteData` 里的硬编码 `0x78` / `0x00` / `0x40` 改成 `OLED_I2C_ADDR` / `OLED_I2C_CMD` / `OLED_I2C_DATA` (2+1+1 = 4 处)。
  - `OLED_Init()` 里的整段 SSD1306 init 序列 (约 20 行) 替换为单行 `OLED_INIT_SEQUENCE();` (宏定义在 `OLED_Controller.h`)。
  - 顶部加 `#include "OLED_Controller.h"`。
  - 函数签名完全不变。

### 怎样换到 SH1106

```c
// 在 include OLED.h 之前:
#define OLED_CONTROLLER  OLED_CTRL_SH1106
// 重新编译。
```

### 怎样换不同 I2C 地址的 SSD1306 模块

```c
#define OLED_I2C_ADDR  0x7A   /* 一些模块用 0x3D 左移 */
```

### 怎样加 SSD1322 / SSD1351 / ILI9341

```c
// 这些控制器的命令集完全不同 (SSD1322 是 4-bit grayscale, ILI9341 是 16-bit color + SPI),
// 选 OLED_CTRL_USER 并提供你自己的 init 序列:
#define OLED_CONTROLLER  OLED_CTRL_USER
#define OLED_INIT_USER() do {                  \
    /* SSD1322 例子 - 列地址 */                  \
    OLED_WriteCommand(0x15); OLED_WriteCommand(0x00); OLED_WriteCommand(0x3F); \
    OLED_WriteCommand(0x75); OLED_WriteCommand(0x00); OLED_WriteCommand(0x3F); \
    OLED_WriteCommand(0x81); OLED_WriteCommand(0x7F); \
    OLED_WriteCommand(0xA0); OLED_WriteCommand(0x53); /* 256x64 */ \
    OLED_WriteCommand(0xA3); OLED_WriteCommand(0x00); \
    OLED_WriteCommand(0xAF); \
} while(0)
```
然后你自己的 init 还得负责把 `OLED_DisplayBuf[OLED_PAGES][OLED_WIDTH]` 写到硬件 (可能需要按 4-bit / 16-bit 重排 — 高层 `OLED_ShowImage` 已经按 byte 写 framebuffer, 你的 init 要保证硬件看到的 framebuffer 格式正确)。

## v2.0 GUI + EXE 重新打包 (2026-06-19)

### GUI 大改

把硬编码 `ttk` 控件升级成现代风格:

* **`_init_style()`**：自动挑选 `vista` / `winnative` / `clam` / `alt` 中可用的 ttk 主题，统一字体 (`TkDefaultFont` size 10)、`TLabelFrame.Label` 加粗、`TButton` 加大 padding、`Accent.TButton` 粗体大 padding 给主操作按钮用。
* **顶栏 (Header bar)**：标题 "图像转字模工具  v2.0" 14pt 粗体 + 副标题 (灰色) + `ttk.Separator`，跟下面所有 LabelFrame 视觉上分开。
* **底部状态栏 (Status bar)**：所有操作 (转换 / 抽帧 / 错误) 都通过 `_update_status(text, level="info"|"warn"|"error")` 写到 `Status.TLabel`，level 改变文字颜色 (#444 / #b35900 / #cc0000)。`WM_DELETE_WINDOW` 退出前也调用。
* **主操作按钮 (开始转换) 升级成 `Accent.TButton`**。
* **视频信息 Label** 用蓝色 (#0066cc) 显示 `codec / fps / 分辨率 / 总帧数`。
* 不再用的 _MAX_DIM / _W / _H 校验保留；现在 `_validate_size` 在 `__init__` 里调一次 (silent)，用户改 W/H 后再调 (有弹窗)。

### 重新打包 EXE

- 跑 `python build.py`，PyInstaller 6.16 自动打包 `dist/CC.exe` (79 MB)。
- 验证 EXE 能正常启动、显示新主题窗口、调用 `_init_style` / `_init_status_bar`、状态栏能更新。
- 因为没装 UPX，size 是 79 MB；装 UPX 后预计能再压 ~30%。
- 一并把根目录的旧 `CC.exe` (74 MB) 替换为新版本 (79 MB)。

### 上传

- commit 进 main, push 到 origin。
- GitHub Release: v0.2 (新), 把新 `CC.exe` 作为 asset 上传。

## v2.0 GUI - 两栏布局 (2026-06-19, 修订)

之前的 v2.0 GUI 把 header / file / screen / params / preview / controls 全部塞在 main_frame 的不同 row 里，960x800 默认窗口下预览和幻灯片都挤到屏幕外。改成 `ttk.PanedWindow` 水平两栏：

### 布局

```
+----------------------------------------------------------------+
|  图像转字模工具  v2.0                                           |   <- 顶栏
|  屏幕、视频、扫描参数可调 · 点击【开始转换】生成 C 字模          |
+----------------------------------------------------------------+
|                                  |                            |
|  [文件设置]   滚动               |  [图像预览]                 |
|  [屏幕尺寸]   ↓                 |  滚动                       |
|  [图像参数]                     |                            |
|  [操作]                         |  [幻灯片播放]               |
|  [激励]                         |                            |
|                                  |                            |
+----------------------------------------------------------------+
|  Ready | W=128 H=64 | v2.0 GUI redesign | ...                    |   <- 状态栏
+----------------------------------------------------------------+
```

### CC.py 改动

* `create_widgets` 重写为四个小方法:
  - `_build_header()` — 顶栏 (title + subtitle, 没有 separator 留更多空间)
  - `_build_left_pane(parent_paned)` — scrollable Canvas + Frame, 装所有 controls, 鼠标滚轮支持
  - `_build_right_pane(parent_paned)` — preview (上, weight=3) + slideshow (下, weight=2)
  - `_build_status_bar()` — 底栏 (status bar)
* `_add_file_section` / `_add_screen_section` / `_add_params_section` / `_add_control_buttons` / `_add_inspire_button` — 拆分原来的 194 行 create_widgets
* 默认窗口从 `960x800` 改为 `1400x900`
* `__init__` 增 `self.status_var = tk.StringVar(value="Ready")` (status bar 需要)

### 用户体验改进

* 预览和幻灯片**永远可见** (在右栏, 不会被控件挤掉)
* 控件多的时候左栏自动滚动 (Canvas + Scrollbar + 鼠标滚轮)
* PanedWindow 的 sash 可拖动调整左/右比例
* 顶栏不再吃掉垂直空间 (header 只有 ~40px 高)

### 测试

* `verify_original.py` 112/112, `verify_custom_size.py` 160/160, `test_convert.py` 全过.
