"""Verify the refactored image_to_font_data matches the original implementation
on a set of synthetic and real test images, across all 16 (direction, order) cases.
"""
import os
import sys
import numpy as np

import tkinter
tk_root = tkinter.Tk()
tk_root.withdraw()

sys.path.insert(0, r"C:\Users\cymr9000p\Desktop\CC\CC字模")

import importlib.util

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

orig = _load("cc_orig", r"C:\Users\cymr9000p\Desktop\CC\CC字模\CC_original.py")
ref  = _load("cc_ref",  r"C:\Users\cymr9000p\Desktop\CC\CC字模\CC.py")

orig_app = orig.ImageToFontConverter(tk_root)
ref_app  = ref.ImageToFontConverter(tk_root)

np.random.seed(42)
test_images = [
    ("zeros",    np.zeros((64, 128), dtype=np.uint8)),
    ("ones",     np.full((64, 128), 255, dtype=np.uint8)),
    ("random",   np.random.randint(0, 2, (64, 128), dtype=np.uint8) * 255),
    ("gradient", np.tile(np.linspace(0, 255, 128, dtype=np.uint8), (64, 1))),
    ("checker",  (np.indices((64, 128)).sum(axis=0) % 2 * 255).astype(np.uint8)),
    ("vlines",   np.tile(np.arange(128) % 8 < 4, (64, 1)).astype(np.uint8) * 255),
    ("hlines",   np.tile(np.arange(64)[:, None] % 8 < 4, (1, 128)).astype(np.uint8) * 255),
]

cases = [
    ("vertical",   "left_to_right_top_to_bottom"),
    ("vertical",   "top_to_bottom_left_to_right"),
    ("vertical",   "right_to_left_top_to_bottom"),
    ("vertical",   "top_to_bottom_right_to_left"),
    ("vertical",   "bottom_to_top_left_to_right"),
    ("vertical",   "left_to_right_bottom_to_top"),
    ("vertical",   "right_to_left_bottom_to_top"),
    ("vertical",   "bottom_to_top_right_to_left"),
    ("horizontal", "left_to_right_top_to_bottom"),
    ("horizontal", "top_to_bottom_left_to_right"),
    ("horizontal", "right_to_left_top_to_bottom"),
    ("horizontal", "bottom_to_top_left_to_right"),
    ("horizontal", "left_to_right_bottom_to_top"),
    ("horizontal", "right_to_left_bottom_to_top"),
    ("horizontal", "top_to_bottom_right_to_left"),
    ("horizontal", "bottom_to_top_right_to_left"),
]

mismatches = 0
total = 0
first_mismatches = []
for d, o in cases:
    for img_name, img in test_images:
        orig_app.scan_direction.set(d)
        orig_app.scan_order.set(o)
        ref_app.scan_direction.set(d)
        ref_app.scan_order.set(o)
        a = orig_app.image_to_font_data(img)
        b = ref_app.image_to_font_data(img)
        if a != b:
            mismatches += 1
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    first_mismatches.append((d, o, img_name, i, x, y))
                    break
        total += 1

print(f"Total: {total} cases, Mismatches: {mismatches}")
for m in first_mismatches[:10]:
    print("  ", m)
sys.exit(0 if mismatches == 0 else 1)
