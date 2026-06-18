# Changelog

## 优化 (2026-06-19)

### CC.py — 主程序

* **`image_to_font_data` 8 路去重**（行为完全保持，112 条回归测试全过）：
  原来 8 个 `for/if/elif` 块（`vertical/horizontal` × 8 个 `scan_order`）共约 200 行。
  现已替换为一张 16 项的 `_FONT_ITER` 派发表 + 1 个 `_pack_byte` 辅助函数，
  整个函数 + 派发表约 70 行，可读性大幅提升，且无 1.0–1.2× 加速。
  派发表里也顺手把原代码里残留的韩语注释
  （`# 만약 검은색 픽셀(값이 0)이면…`、`# 고위가 앞쪽`）替换为清晰的中文说明。

* **`convert_images` 修 3 个隐藏 bug**：
  1. 之前不管目录里有几张图，`.h` 文件总是写 25 个 `extern const uint8_t IMG_DATAxx[];`，
     在 `len(image_files) < 25` 时会引入未定义引用导致链接失败；
     现在只写实际生成的 `IMG_DATA1..N`。
  2. 之前 `image_files` 会把尺寸不对的图片也囊括进来，而转换循环又用 `continue` 跳过，
     导致 `gif()` 里的 `for i in range(len(image_files))` 引用了不存在的符号；
     现在用 `_list_valid_images` 一次性过滤掉非 128×64 或无法读取的图。
  3. `_format_hex_array` 把原来手工写的 16 字节换行抽成辅助函数，
     跟派发表一样重复的循环体都被收拢。

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

* **`show_inspire_image`** 加 `<Destroy>` 绑定清理对图片的引用，避免窗口关闭后仍被引住。

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

### oled/ — 库代码未改动

`OLED.c/h` 是 `gd32vw55x` 的硬件驱动（来自桨协科技），
保持原样以免影响已部署的硬件；其中的 `round()` / `atan2()` 重新实现是为了在某些裸机工具链
没有 `libm` 时仍能编译，也未动。

### 新增测试脚本

* `verify_original.py`：跨 7 张合成图 × 16 个 `(direction, order)` 组合 = 112 条用例，
  验证 `image_to_font_data` 与重构前行为字节级一致。
* `test_convert.py`：功能测试 — 空目录报警、过滤掉非 128×64 图、
  生成正确的 `.c`/`.h`、头文件不再有 25 个占位声明。
* `bench.py`：微基准。

### 文件清单

```
CC字模/
├── CC.py              (38945  bytes,  原 47137  −17%)
├── CC_original.py     (原版, 仅供回归测试对比)
├── build.py           (5620   bytes,  原 4239,  功能更多)
├── resources.py       (265251 bytes,  原 ~342000  −22%)
├── cym_icon.ico       (未改)
├── verify_original.py (新增,  回归测试)
├── test_convert.py    (新增,  功能测试)
├── bench.py           (新增,  性能基准)
└── CHANGELOG.md       (本文件)
```

跑回归测试：

```bash
cd CC字模
python verify_original.py   # 期望: Total: 112 cases, Mismatches: 0
python test_convert.py      # 期望: All convert_images tests passed.
python bench.py             # 期望: speedup >= 1.0x
```

重新打包（需要先 `pip install pyinstaller`）：

```bash
cd CC字模
python build.py            # 单 exe   → dist/CC.exe
python build.py --onedir   # 目录模式 → dist/CC/CC.exe
```
