"""Benchmark image_to_font_data across multiple sizes and orders.

Compares the refactored implementation against the very original
(CC_original.py) and the intermediate version (CC_pre_custom_size.py).
"""
import sys
import time
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
ref = _load("cc_ref", r"C:\Users\cymr9000p\Desktop\CC\CC字模\CC.py")
app = ref.ImageToFontConverter(tk_root)

SIZES = [(128, 64), (96, 16), (256, 64), (64, 128)]
ORDERS = [("vertical", "left_to_right_top_to_bottom"),
          ("vertical", "bottom_to_top_right_to_left"),
          ("horizontal", "right_to_left_top_to_bottom"),
          ("horizontal", "bottom_to_top_right_to_left")]
N = 50
np.random.seed(42)
print(f"benchmarking {N} iterations each")
print(f"{'size':>10} {'direction':>10} {'order':>30} {'ms/iter':>10} {'bytes':>8}")
for W, H in SIZES:
    assert app._validate_size(W, H, silent=True)
    img = np.random.randint(0, 2, (H, W), dtype=np.uint8) * 255
    for d, o in ORDERS:
        app.scan_direction.set(d); app.scan_order.set(o)
        t0 = time.perf_counter()
        for _ in range(N):
            app.image_to_font_data(img)
        t1 = time.perf_counter()
        ms = 1000 * (t1 - t0) / N
        print(f"  {W:>3}x{H:<3}    {d:>10} {o:>30} {ms:>10.2f} {W*H//8:>8}")
