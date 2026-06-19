# CC — 图像/视频转 OLED 字模工具

> 把图片或视频批量转成 OLED 屏幕用的 C 语言字模数组，一键生成可直接烧录到 MCU 的 `.c` / `.h` 文件。
> 同时附带一份已参数化的 SSD1306 风格 C 驱动 (`oled/OLED.c`)，可裁剪到任何 8 的倍数屏幕尺寸。

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License: BSL-1.0](https://img.shields.io/badge/license-BSL--1.0-blue.svg)](LICENSE)
[![Platform: Windows / macOS / Linux](https://img.shields.io/badge/platform-win%20%7C%20macos%20%7C%20linux-lightgrey)]()

---

## 目录

- [它能做什么](#它能做什么)
- [效果预览](#效果预览)
- [快速开始](#快速开始)
- [界面说明](#界面说明)
- [支持的屏幕尺寸](#支持的屏幕尺寸)
- [支持的视频格式](#支持的视频格式)
- [生成的 C 代码长什么样](#生成的-c-代码长什么样)
- [硬件集成](#硬件集成)
- [配置持久化](#配置持久化)
- [打包为单文件 EXE](#打包为单文件-exe)
- [开发与测试](#开发与测试)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [许可](#许可)

---

## 它能做什么

- **图像 → C 字模**：把一个文件夹里的所有 128×64 (或自定义 W×H) PNG/JPG/BMP 一键转成 `IMG_DATA1[]`、`IMG_DATA2[]`、... 字节数组，并生成一个配套 `gif()` 函数自动按幻灯片间隔播放。
- **视频 → 图像 → C 字模**：从 mp4 / webm / mkv / avi / flv / wmv / m4v / 3gp / ts / m2ts / mpg / ogv / vob / rm 等任意 FFmpeg 支持的容器里按帧间隔抽帧，再走相同的转换流程。
- **可调参数**：亮度、对比度、旋转 0/90/180/270°、水平/垂直镜像、反色、扫描方向（vertical/horizontal）、8 种扫描顺序。
- **自定义屏幕尺寸**：W、H 可设到 16384 (16K 屏幕字面含义)；非 8 的倍数自动向上 padding 并在生成代码里写明。
- **C 驱动 `#define` 可配置**：`oled/OLED.h` 改 3 个尺寸宏 (`OLED_WIDTH` / `OLED_HEIGHT` / `OLED_PAGES`) + 4 个 I2C 宏 (`OLED_I2C_ADDR` / `OLED_I2C_CMD` / `OLED_I2C_DATA` / `OLED_CONTROLLER`) 适配 SSD1306 / SH1106 / 自定义控制器；函数签名不变。

## 效果预览 (v0.3 两栏布局)

现代 ttk vista/clam 主题, 两栏布局 (左 controls 滚动 / 右 preview+slideshow 永远可见), 顶栏带版本号标题, 底栏 status bar。

```
┌─────────────────────────────────────────────────────────────┐
│  图像转字模工具                                              │
│  ┌─ 文件设置 ─────────────────────────────────────────────┐ │
│  │  图像文件夹: [C:\Users\you\Pictures\gif\        ] [...]  │ │
│  │  输出文件:   [C:\Users\you\out.c                ] [...]  │ │
│  │  视频文件:   [C:\Users\you\demo.mp4            ] [...]  │ │
│  │  帧间隔: [30] 帧 [从视频生成图片]                       │ │
│  │  codec: h264 | 30.0 fps | 1920x1080 | 1234 frames        │ │
│  │  [████████████░░░░░░░] 60%  frame 740/1234 saved 24     │ │
│  │  [pause]                                               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ 屏幕尺寸 (8 的倍数; 上限 16384) ─────────────────────┐ │
│  │  宽 (W): [128]  高 (H): [64]  [应用到图像处理]          │ │
│  │  (非 8 倍会自动 pad; 改 C 端 oled/OLED.h 顶部 #define…) │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ 图像参数调节 ─────────────────────────────────────────┐ │
│  │  亮度: [────●──────] 0                                  │ │
│  │  对比度: [──────●──] 1.50                               │ │
│  │  ☐ 反色   旋转: ◉ 0°  ○ 90°  ○ 180°  ○ 270°             │ │
│  │  ☐ 水平镜像   ☐ 垂直镜像                              │ │
│  │  扫描方向: ◉ vertical  ○ horizontal                    │ │
│  │  扫描顺序: ◉ L→R, T→B   ○ T→B, L→R   ○ R→L, T→B ...     │ │
│  │  幻灯片间隔(ms): [500]  ☐ 实时预览                     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ 图像预览 ─────────────────────┐ ┌─ 幻灯片播放 ─────┐ │
│  │  [img_00][img_01][img_02]      │ │                  │ │
│  │  [img_03][img_04][img_05]      │ │  (2× 缩放)        │ │
│  │  [img_06][img_07][img_08]      │ │  [播放][停止]    │ │
│  └────────────────────────────────┘ └──────────────────┘ │
│                                            [刷新预览][开始转换]  │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 装依赖

```bash
pip install opencv-python numpy pillow
# tkinter 是 Python 自带；Windows / 官方 macOS / 大多数 Linux 发行版默认已装
```

### 2. 运行（开发模式）

```bash
cd CC字模
python CC.py
```

### 3. 或者直接用预编译的 `CC.exe`

[Release 页面](https://github.com/cym9196/CC/releases) 下载最新 `CC.exe` (约 79 MB, v0.3 两栏布局) 双击即可。

## 界面说明

| 区域 | 作用 |
|---|---|
| **文件设置** | 选图像文件夹、输出 `.c` 文件、视频文件、帧间隔 |
| **视频编码/进度** | 选中视频后自动显示 `codec / fps / 分辨率 / 总帧数`；抽帧时显示进度条 + `frame X/Y saved N`；可暂停/恢复 |
| **屏幕尺寸** | W、H 输入 + "应用到图像处理" 按钮（必须 8 的倍数，上限 16384） |
| **图像参数调节** | 亮度、对比度、反色、旋转、镜像、扫描方向 (vertical/horizontal)、8 种扫描顺序、幻灯片间隔 |
| **图像预览** | 一次显示前 16 张图的处理结果 |
| **幻灯片播放** | 在 2× 缩放的画布上按选定间隔循环播放 |
| **控制按钮** | 刷新预览 / 开始转换 / 退出 + 激励按钮（彩蛋） |

## 支持的屏幕尺寸

- 硬上限：**16384 × 16384**（"16K 屏幕"字面含义）。
- W、H 都必须是 **8 的倍数**（SSD1306 / 其他 1 字节 8 像素控制器的硬要求）。
- 非 8 倍输入会被自动向上 pad 到下一个 8 倍，并在生成的 C 代码首行加注释：
  ```c
  // OLED font matrix data - 104x32  (NOTE: requested WxH was padded to 104x32)
  ```
  pad 区域填白色。

C 端需要同步修改 `oled/OLED.h` 顶部 3 个 `#define`：
```c
#ifndef OLED_WIDTH
#define OLED_WIDTH  128   // 改成你的实际宽度
#endif
#ifndef OLED_HEIGHT
#define OLED_HEIGHT 64    // 改成你的实际高度
#endif
#define OLED_PAGES  ((OLED_HEIGHT + 7) / 8)
```

支持的常见尺寸示例：

| W × H | 字节数/图 | 适用 |
|---|---|---|
| 128 × 64 | 1024 | SSD1306 0.96" OLED（默认） |
| 128 × 32 | 512 | SSD1306 0.91" OLED |
| 96 × 16 | 192 | 小尺寸 SSD1306 |
| 256 × 64 | 2048 | SSD1322 2.4" OLED |
| 64 × 128 | 1024 | 竖屏 SSD1306 |
| 1024 × 256 | 32 768 | 大屏 (需要足够 RAM) |

## 支持的视频格式

文件对话框里列出 19 种常见容器（`mp4 / avi / mov / mkv / webm / flv / wmv / m4v / 3gp / ts / m2ts / mpg / mpeg / ogv / vob / rm / rmvb / asf`），但 **实际可读范围由 OpenCV 自带的 FFmpeg 决定**——比这多得多，少见格式基本都覆盖。选中后自动显示：

```
codec: h264 | 30.0 fps | 1920x1080 | 1234 frames
```

抽帧时：

- 进度条实时更新（`frame 740/1234 saved 24`）。
- 总帧数未知时切到 indeterminate 模式（动画条）。
- **Pause / Resume** 按钮可在任意时刻暂停和继续；暂停时 worker 在 `Event.wait()` 阻塞，主线程不卡。
- 损坏帧（`cv2` 返回 `None`）计入 `corrupt` 计数并跳过；完成后 messagebox 报告 `extracted N frames  (M corrupt frames skipped)`。

## 生成的 C 代码长什么样

`out.c` 例子（96×16 屏，2 张图）：

```c
// OLED font matrix data - 96x16
#include <stdint.h>

const uint8_t IMG_DATA1[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0x00, 0x00, 0x00, 0x00,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    // ... 192 bytes total (96*16/8)
};

const uint8_t IMG_DATA2[] = {
    // ...
};

// total: 2 image(s)
// OLED_ShowImage calls below use (96, 16)
void gif(void) {
    OLED_ShowImage(0,0,96,16,IMG_DATA1);OLED_Update();delay_1ms(500);OLED_Clear();
    OLED_ShowImage(0,0,96,16,IMG_DATA2);OLED_Update();delay_1ms(500);OLED_Clear();
}
```

`out.h`：

```c
#ifndef __OUT_H
#define __OUT_H

#include <stdint.h>

extern const uint8_t IMG_DATA1[];
extern const uint8_t IMG_DATA2[];

extern void gif(void);

#endif // __OUT_H
```

注意：以前版本总是 padding 到 25 个 `extern`，导致 `len(image_files) < 25` 时链接失败；新版本只写实际生成的 N 个（已修复）。

## 硬件集成

仓库里附带一份**已参数化**的 SSD1306 风格 C 驱动（来自 [jiangxiekeji](https://jiangxiekeji.com)，BSL 协议）：

```
oled/
├── OLED.c               # ~52 KB, 全部循环已用 OLED_WIDTH/OLED_PAGES 参数化
├── OLED.h               # 顶部 3 个尺寸 + 6 个 I2C/控制器 #define
├── OLED_Controller.h    # 按 OLED_CONTROLLER 切换 init 序列 (SSD1306 / SH1106 / USER)
├── OLED_Data.c          # 字库数据（ASCII 6x8 / 8x16 / 中文 16x16）
└── OLED_Data.h
```

### 在你的 STM32 / GD32 工程里用

1. 把 `oled/` 整个目录加进工程。
2. 在 `main.c` 里 `OLED_Init();`，然后 `gif();` 就能循环播放。
3. **换屏幕尺寸**只改 `OLED.h` 顶部 3 行：
   ```c
   #define OLED_WIDTH  96
   #define OLED_HEIGHT 16
   ```
4. 重新编译即可。

### 换 I2C 控制器

`OLED.h` 顶部还有 4 个 `#define` 控制 I2C 协议本身（不需要碰 `OLED.c`）：

| 宏 | 默认 | 用途 |
|---|---|---|
| `OLED_I2C_ADDR` | `0x78` | I2C 从机地址字节 (SSD1306)。**SH1106 用 0x7A** |
| `OLED_I2C_CMD` | `0x00` | 控制字节：命令流 |
| `OLED_I2C_DATA` | `0x40` | 控制字节：数据流 |
| `OLED_CONTROLLER` | `OLED_CTRL_SSD1306` | 见下表 |

| `OLED_CONTROLLER` 值 | 适配 | 备注 |
|---|---|---|
| `OLED_CTRL_SSD1306` (0) | 0.96" / 1.3" SSD1306 | 默认 |
| `OLED_CTRL_SH1106` (1) | 1.3" SH1106 | charge pump / precharge / vcomh 微调 |
| `OLED_CTRL_USER` (2) | SSD1322 / SSD1351 / ILI9341 / 你自己的 | **必须** `#define OLED_INIT_USER() { 你的 init 命令 }` |

**示例 1：换 SH1106**

```c
// 放在 include OLED.h 之前
#define OLED_CONTROLLER  OLED_CTRL_SH1106
```

**示例 2：换 0x7A 地址的 SSD1306 模块**

```c
#define OLED_I2C_ADDR  0x7A
```

**示例 3：加 SSD1322 (256x64, 4-bit grayscale)**

```c
#define OLED_CONTROLLER  OLED_CTRL_USER
#define OLED_INIT_USER() do {                                  \
    OLED_WriteCommand(0x15); OLED_WriteCommand(0x00);         \
    OLED_WriteCommand(0x3F);                                  \
    OLED_WriteCommand(0x75); OLED_WriteCommand(0x00);         \
    OLED_WriteCommand(0x3F);                                  \
    OLED_WriteCommand(0xA0); OLED_WriteCommand(0x53);         \
    OLED_WriteCommand(0xA3); OLED_WriteCommand(0x00);         \
    OLED_WriteCommand(0xAF);                                  \
} while(0)
```

SSD1322 是 4-bit grayscale，`OLED_DisplayBuf` 是按 8-bit 组织的——你的 `OLED_UpdateArea` 实现需要把 byte 拆成两个 nibble 再写。`OLED_ShowImage` 接口不变，硬件层你看着办。

> **16K 满配警告**：`OLED_DisplayBuf[OLED_PAGES][OLED_WIDTH]` 在 16Kx16K 是 **256 MB**，远超任何 MCU 的 RAM。请按你的硬件能力选尺寸。

## 配置持久化

启动时自动加载上次设置，关闭时自动保存到：

| OS | 路径 |
|---|---|
| Windows | `C:\Users\<you>\.cym_cc_config.json` |
| macOS / Linux | `~/.cym_cc_config.json` |

保存的参数（14 个）：

```json
{
  "width": 128,
  "height": 64,
  "image_folder": "C:/Users/you/Pictures/gif/",
  "output_file": "C:/Users/you/out.c",
  "video_file": "",
  "scan_direction": "vertical",
  "scan_order": "left_to_right_top_to_bottom",
  "slideshow_interval": 500,
  "video_frame_interval": 30,
  "brightness": 0,
  "contrast": 1.0,
  "rotation": "0",
  "invert_color": false,
  "horizontal_flip": false,
  "vertical_flip": false
}
```

失败静默（权限/磁盘满都不打扰用户）。

## 打包为单文件 EXE

```bash
cd CC字模
pip install pyinstaller
python build.py            # 单文件 -> dist/CC.exe
python build.py --onedir   # 目录模式 -> dist/CC/CC.exe（启动更快）
```

`build.py` 会自动：
- 扫描 `cym_icon.ico` 和 `picture/` 目录，把所有图片用 `bytes` 字面量（不再是 base64）嵌进 `resources.py`。
- 写一个 UPX 探测，没装 UPX 时 `WARNING` 而不是默默跳过。
- 预先剔除 `matplotlib / scipy / pandas / PyQt* / IPython / pytest / librosa / sklearn / pydoc / doctest` 等绝对用不到的重模块。

## 开发与测试

```bash
cd CC字模

# 128×64 行为回归（112 条用例，跨 16 个 (direction, order) × 7 张合成图）
python verify_original.py
# 期望: Total: 112 cases, Mismatches: 0

# 自定义尺寸行为（160 条用例：5 尺寸 × 2 方向 × 8 order × 2 图）
python verify_custom_size.py
# 期望: Total: 160 cases, Fails: 0

# convert_images 功能测试（128×64 / 96×16 / 100×30 pad / 空目录）
python test_convert.py
# 期望: All convert_images tests passed.

# 性能基准（4 尺寸 × 4 order）
python bench.py
# 128×64 ~1.5 ms/iter,  96×16 ~0.3 ms/iter,  256×64 ~2.9 ms/iter
```

回归测试覆盖了关键的 bottom_to_top 边界 quirk（已固化的旧行为，故意保留以兼容历史生成的 C 数组）。

## 项目结构

```
CC/
├── CC.exe                       # 预编译的可执行文件（Release 页面下载）
├── CC.zip                       # 整个项目的压缩包
├── LICENSE                      # BSL-1.0
├── README.md                    # 本文件
├── oled/                        # SSD1306 风格 C 驱动
│   ├── OLED.c                   #   已参数化
│   ├── OLED.h                   #   顶部 3 个 #define
│   ├── OLED_Data.c
│   └── OLED_Data.h
└── CC字模/                      # 主体（Python 工具）
    ├── CC.py                    # 主程序
    ├── CC_original.py           # 最初版（供回归测试对比）
    ├── build.py                 # PyInstaller 打包脚本
    ├── resources.py             # 自动生成的图标内嵌（bytes 字面量，265 KB）
    ├── cym_icon.ico             # 应用图标
    ├── verify_original.py       # 128×64 回归测试
    ├── verify_custom_size.py    # 自定义尺寸测试
    ├── test_convert.py          # convert_images 功能测试
    ├── bench.py                 # 性能基准
    ├── CHANGELOG.md             # 详细变更日志
    └── .gitignore
```

## 常见问题

**Q: 生成的 C 文件怎么用？**
A: 直接 `#include "out.h"`，在主循环里调 `gif();`。需要 `delay_1ms(uint32_t ms)` 这个延时函数（你的工程里自己提供；HAL 库里通常用 `HAL_Delay` 替代）。

**Q: 选 W=100 H=30 会发生什么？**
A: 内部 pad 到 104×32（多 4 列、2 行白色），生成的 C 代码首行会写明 `requested WxH was padded to 104x32`，用户需在硬件侧忽略多余列/行。

**Q: 视频转出来的图片有水印 / 字幕怎么办？**
A: 视频本身有的话没法自动去掉，**生成前**用其它工具去水印。本工具不做视频编辑。

**Q: 16K 屏幕真的能跑吗？**
A: 取决于你 MCU 的 RAM。`OLED_DisplayBuf` 在 16K×16K 是 256 MB，没有任何 MCU 能装下。**实际可用尺寸**取决于你的硬件 + 编译器，建议先按你的屏幕真实分辨率设 W、H，剩下交给 `#define` 编译期检查。

**Q: 为什么保留了 `bottom_to_top` col-major 的 boundary quirk（行 63, 55, …, 7 而不是 56, 48, …, 0）？**
A: 这是原代码就有的 bug，但用户已经用这个 byte 序列烧过固件了，修复会导致已部署的 C 数组错位。112 条回归测试已经把它固化下来；如果你想从零开始、可以重写 `_make_iter` 里 `bottom_to_top_left_to_right` 的 horizontal col-major 分支为 `range(H - 8, -1, -8)`。

**Q: 怎么减小 EXE 体积？**
A: 装 [UPX](https://upx.github.io/) 即可（再压 30%）。`build.py` 会自动检测。其他手段比如替换 `opencv-python` 为 `opencv-python-headless` 省 20 MB；想自己定义，参见 [build.py](CC字模/build.py) 的 `EXCLUDED_MODULES`。

## 许可

本项目以 [Boost Software License 1.0](LICENSE) 发布。

附带 C 驱动 `oled/OLED.c` 来自 [jiangxiekeji.com](https://jiangxiekeji.com)（桨协科技），同样 BSL-1.0 许可。
