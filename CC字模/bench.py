"""Benchmark the original vs refactored image_to_font_data."""
import sys, time
import numpy as np
import tkinter
tk_root = tkinter.Tk(); tk_root.withdraw()
sys.path.insert(0, r'C:\Users\cymr9000p\Desktop\CC\CC字模')
import importlib.util
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
orig = _load('cc_orig', r'C:\Users\cymr9000p\Desktop\CC\CC字模\CC_original.py')
ref  = _load('cc_ref',  r'C:\Users\cymr9000p\Desktop\CC\CC字模\CC.py')
o_app = orig.ImageToFontConverter(tk_root); r_app = ref.ImageToFontConverter(tk_root)
np.random.seed(42)
img = np.random.randint(0, 2, (64, 128), dtype=np.uint8) * 255
N = 200
for d, o in [('vertical', 'left_to_right_top_to_bottom'),
             ('vertical', 'bottom_to_top_right_to_left'),
             ('horizontal', 'right_to_left_top_to_bottom')]:
    o_app.scan_direction.set(d); o_app.scan_order.set(o)
    r_app.scan_direction.set(d); r_app.scan_order.set(o)
    t0 = time.perf_counter()
    for _ in range(N):
        o_app.image_to_font_data(img)
    t1 = time.perf_counter()
    for _ in range(N):
        r_app.image_to_font_data(img)
    t2 = time.perf_counter()
    print(f'{d:10} {o:30} orig={1000*(t1-t0)/N:.2f}ms  ref={1000*(t2-t1)/N:.2f}ms  speedup={(t1-t0)/(t2-t1):.1f}x')
