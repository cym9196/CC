"""Functional test for convert_images: stub out the GUI dependencies, run the
conversion, and verify the generated C files are well-formed."""
import os
import sys
import tempfile
import shutil
import numpy as np
import cv2
import tkinter

# Stub messagebox and filedialog so the module loads and runs without user prompts
import tkinter.messagebox as mb
mb_calls = []
def fake_showinfo(*args, **kwargs):
    mb_calls.append(("info", args, kwargs))
def fake_showwarning(*args, **kwargs):
    mb_calls.append(("warning", args, kwargs))
def fake_showerror(*args, **kwargs):
    mb_calls.append(("error", args, kwargs))
mb.showinfo = fake_showinfo
mb.showwarning = fake_showwarning
mb.showerror = fake_showerror

tk_root = tkinter.Tk(); tk_root.withdraw()
sys.path.insert(0, r'C:\Users\cymr9000p\Desktop\CC\CC字模')
import importlib.util
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
mod = _load('cc_t', r'C:\Users\cymr9000p\Desktop\CC\CC字模\CC.py')
app = mod.ImageToFontConverter(tk_root)

tmp = tempfile.mkdtemp()
try:
    # Create 3 test images
    for i, pat in enumerate([
        np.zeros((64, 128), dtype=np.uint8),  # all black
        np.full((64, 128), 255, dtype=np.uint8),  # all white
        (np.indices((64, 128)).sum(axis=0) % 2 * 255).astype(np.uint8),  # checker
    ]):
        cv2.imwrite(os.path.join(tmp, f"img_{i:02d}.png"), pat)
    # Also add an image with wrong size to ensure it's filtered
    cv2.imwrite(os.path.join(tmp, "wrong_size.png"), np.zeros((100, 100), dtype=np.uint8))

    out_c = os.path.join(tmp, "out.c")
    app.image_folder.set(tmp)
    app.output_file.set(out_c)
    app.convert_images()
    print(f"convert_images called, messagebox calls: {len(mb_calls)}")
    for kind, args, _ in mb_calls:
        print(f"  {kind}: {args[0]}")

    # Check that the .c and .h files were created
    out_h = out_c[:-2] + ".h"
    assert os.path.exists(out_c), f"missing {out_c}"
    assert os.path.exists(out_h), f"missing {out_h}"

    c_text = open(out_c, encoding="utf-8").read()
    h_text = open(out_h, encoding="utf-8").read()

    # Should have exactly 3 IMG_DATA arrays (filter excluded the wrong_size.png)
    assert c_text.count("const uint8_t IMG_DATA") == 3, f"unexpected array count in .c:\n{c_text}"
    # Header should have exactly 3 extern declarations
    assert h_text.count("extern const uint8_t IMG_DATA") == 3, f"unexpected extern count in .h:\n{h_text}"
    # Header should NOT contain IMG_DATA4 (no padding to 25)
    assert "IMG_DATA4" not in h_text, f"header was padded to 4+! h_text=\n{h_text}"
    # Both should reference gif()
    assert "void gif(void)" in c_text
    assert "extern void gif(void);" in h_text
    # The first array (all-black) should be 0xFF 1024 times
    assert "0xFF" in c_text
    print("\n.c content (first 300 chars):\n", c_text[:300])
    print("\n.h content:\n", h_text)
finally:
    shutil.rmtree(tmp)

# Also test that empty folder shows a warning and does NOT create files
mb_calls.clear()
tmp2 = tempfile.mkdtemp()
try:
    out_c2 = os.path.join(tmp2, "out.c")
    app.image_folder.set(tmp2)
    app.output_file.set(out_c2)
    app.convert_images()
    assert not os.path.exists(out_c2), "should not create file for empty folder"
    assert any("warning" in c[0] for c in mb_calls), "expected warning for empty folder"
    print("\nEmpty folder case: OK (got warning, no file created)")
finally:
    shutil.rmtree(tmp2)
print("\nAll convert_images tests passed.")
