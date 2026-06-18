"""Test image_to_font_data across multiple screen sizes.

For each size in SIZES, run all 16 (direction, order) combinations on 2
synthetic images, checking that the byte count matches W*H/8 and the output
is non-degenerate (not all zeros, not all 0xFF on a non-uniform image).
"""
import sys
import numpy as np
import tkinter
import tkinter.messagebox as mb
mb.showerror = lambda *a, **k: None
mb.showinfo = lambda *a, **k: None
mb.showwarning = lambda *a, **k: None
tk_root = tkinter.Tk(); tk_root.withdraw()
sys.path.insert(0, r"C:\Users\cymr9000p\Desktop\CC\CC字模")
import importlib.util
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
mod = _load("cc_t", r"C:\Users\cymr9000p\Desktop\CC\CC字模\CC.py")
app = mod.ImageToFontConverter(tk_root)

SIZES = [(128, 64), (128, 32), (96, 16), (256, 64), (64, 128)]
ORDERS = [
    "left_to_right_top_to_bottom", "top_to_bottom_left_to_right",
    "right_to_left_top_to_bottom", "top_to_bottom_right_to_left",
    "bottom_to_top_left_to_right", "left_to_right_bottom_to_top",
    "right_to_left_bottom_to_top", "bottom_to_top_right_to_left",
]
np.random.seed(123)
total = 0
fails = 0
for W, H in SIZES:
    assert app._validate_size(W, H, silent=True), f"size {W}x{H} rejected"
    assert app._W == W and app._H == H, f"size mismatch {app._W}x{app._H}"
    nbytes = W * H // 8
    # Test image: gradient
    img = np.tile(np.linspace(0, 255, W, dtype=np.uint8), (H, 1))
    # Test image: random
    img2 = np.random.randint(0, 2, (H, W), dtype=np.uint8) * 255
    for d in ("vertical", "horizontal"):
        for o in ORDERS:
            for label, im in [("gradient", img), ("random", img2)]:
                app.scan_direction.set(d); app.scan_order.set(o)
                data = app.image_to_font_data(im)
                if len(data) != nbytes:
                    fails += 1
                    print(f"FAIL {W}x{H} {d}/{o}/{label}: got {len(data)} bytes, expected {nbytes}")
                elif label == "random" and not (min(data) < max(data)):
                    fails += 1
                    print(f"FAIL {W}x{H} {d}/{o}/random: all bytes equal ({data[0]})")
                total += 1
print(f"Total: {total} cases, Fails: {fails}")
sys.exit(0 if fails == 0 else 1)
