# -*- coding: utf-8 -*-
"""
_encode_qr.py - helper to regenerate qrcode_b64.py from a JPG/PNG file.

Usage:
    python _encode_qr.py path/to/your-qrcode.jpg
    python _encode_qr.py path/to/your-qrcode.png

This overwrites qrcode_b64.py in the same directory. After running it, you
should run `python build.py` to embed the new QR code into resources.py
and rebuild the EXE.

The original jpg/png is gitignored (see .gitignore) so it never enters
version control. Only the base64 string in qrcode_b64.py is committed.
"""
import base64
import io
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print(__doc__)
    sys.exit(1)

src = Path(sys.argv[1])
if not src.is_file():
    print(f"ERROR: {src} not found")
    sys.exit(1)

dst = Path(__file__).parent / "qrcode_b64.py"

raw = src.read_bytes()
b64 = base64.b64encode(raw).decode("ascii")

# Get dimensions
try:
    from PIL import Image
    w, h = Image.open(io.BytesIO(raw)).size
except Exception:
    w, h = 0, 0

lines = []
for i in range(0, len(b64), 76):
    lines.append('    "' + b64[i:i+76] + '"')

docstring = (
    "qrcode_b64.py - Author QR code, embedded as base64.\n"
    "\n"
    "This file is the source of truth for the QR code displayed when the user\n"
    "clicks the support-author button in the GUI.\n"
    "\n"
    "To replace the QR code:\n"
    "  1. Save your new QR code image as jili.jpg (any size, JPG/PNG)\n"
    "  2. Run: python _encode_qr.py jili.jpg > qrcode_b64.py\n"
    "  3. Re-run: python build.py  (embeds it into resources.py -> CC.exe)\n"
    "\n"
    "Why base64:\n"
    "  - The original jpg would be a ~200 KB binary blob in git, hard to diff\n"
    "    and easy to leak personal info (account name in the QR card).\n"
    "  - Base64 in a .py file is plain text, easy to review in PRs, and the\n"
    "    .jpg source file is gitignored so it never leaves your machine.\n"
    "\n"
    f"Source file:    {src.name}\n"
    f"Original size: {len(raw)} bytes ({w} x {h} px)\n"
    f"Encoded size:  {len(b64)} chars\n"
)

content = '# -*- coding: utf-8 -*-\n'
content += '"""' + docstring + '"""\n\n'
content += '# Original image bytes, base64-encoded.\n'
content += '# decode with: base64.b64decode(QRCODE_JPG_B64)\n'
content += 'QRCODE_JPG_B64 = (\n'
content += '\n'.join(lines)
content += '\n)\n\n'
content += '# Image dimensions (used to size the Toplevel window before decoding).\n'
content += f'QRCODE_WIDTH = {w}\n'
content += f'QRCODE_HEIGHT = {h}\n\n\n'
content += 'def get_bytes():\n'
content += '    """Return the raw image bytes of the QR code (decoded from base64)."""\n'
content += '    import base64\n'
content += '    return base64.b64decode(QRCODE_JPG_B64)\n'

dst.write_text(content, encoding="utf-8")
print(f"Wrote {dst} ({len(content)} bytes)")
print(f"  Source:    {src}")
print(f"  Original:  {len(raw)} bytes ({w}x{h})")
print(f"  Encoded:   {len(b64)} chars")
print()
print("Next: run `python build.py` to embed the new QR code into the EXE.")
