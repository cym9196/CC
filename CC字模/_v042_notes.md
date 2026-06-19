# CC v0.4.2 — 收款二维码 (base64 嵌入)

把 v0.4.1 的激励图片 (作者微信支付收款二维码) 从"jpg 嵌入 resources.py"升级为"base64 源码嵌入"。原因是 jpg 二进制进入 git 后无法审计/diff, 容易泄露作者真实姓名等个人信息。

## 改动

### 1. 新增 `qrcode_b64.py` (286 KB)

源码里就是收款二维码, base64 编码形式:

```python
QRCODE_JPG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQE..."
    # 共 261308 字符, 76 字符一行, 可读可 diff
)

QRCODE_WIDTH = 1409
QRCODE_HEIGHT = 1920

def get_bytes():
    """Return the raw JPG bytes of the QR code (decoded from base64)."""
    import base64
    return base64.b64decode(QRCODE_JPG_B64)
```

### 2. 新增 `_encode_qr.py` 辅助脚本

```bash
python _encode_qr.py jili.jpg   # 重新生成 qrcode_b64.py
```

自动读取图片尺寸填入 `QRCODE_WIDTH/HEIGHT`, 把 jpg 转 base64。

### 3. `build.py` 改造

加载优先级:
1. **qrcode_b64.py** (base64 源码) — 唯一 source of truth
2. 磁盘 `jili.jpg` / `jili.png` — 开发者本地 fallback, **gitignored**
3. `picture/` 目录 — 其它图片

### 4. `show_inspire_image` 重写

* 标题: `💰 支持作者 — CC v0.4.2`
* 按钮: `[💸 已支付, 感谢支持]` `[关闭]` (去掉 GitHub Star 按钮, 收款场景不需要)
* 4 级 fallback: `qrcode_b64.py` → 磁盘 jpg → 磁盘 png → `resources.RESOURCES` → 文字兜底
* 自适应屏幕: 屏幕小时按比例缩小, 永远保持原始 1409:1920 宽高比 (QR 码不变形, 永远可扫)
* 状态栏显示加载来源 (`qrcode_b64.py (embedded base64)` 等)

### 5. 操作 tab 按钮文字

`激励 (额外)` → `💰 支持作者 (扫码赠送)`

### 6. `.gitignore` 更新

```
jili.jpg
jili.png
jili.jpeg
```

源头 jpg **不再进 git**, 只进 base64 源码。

## untrack

本 release untrack 了 `CC字模/jili.jpg` 和 `jili.png` (文件保留在本地, 不再被 git 追踪)。

**⚠️ 隐私提示**: 旧 commit `3b886c2` (v0.4.1) 里的 jili.jpg 仍在 git 历史中。如要彻底删除需 `git filter-branch` (heavy 操作, 由用户决定是否做)。

## 测试

* `verify_original.py`: **112/112 通过**
* `verify_custom_size.py`: **160/160 通过**
* `show_inspire_image` 弹窗测试: QR 码完整显示, 标题/按钮/缩放全部正常

## 下载

* `CC.exe` (~80 MB, PyInstaller, Windows 64-bit)
* 源码: `git clone https://github.com/cym9196/CC`
* 详细: `README.md` + `CHANGELOG.md`

## 链接

* Release: https://github.com/cym9196/CC/releases/tag/v0.4.2
* 上一版: [v0.4.1](https://github.com/cym9196/CC/releases/tag/v0.4.1)
