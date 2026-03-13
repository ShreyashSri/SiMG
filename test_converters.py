"""
Standalone test suite for verifying converter and evil_converter behaviors.
Usage: python3 test_converters.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "converter"))

import numpy as np
from PIL import Image
import tempfile, pydicom, pydicom.data

GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"; BOLD = "\033[1m"
def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗ FAIL:{RESET} {msg}"); sys.exit(1)
def info(msg): print(f"  {YELLOW}→{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

header("Setup: Loading sample DICOM")
DICOM_PATH = pydicom.data.get_testdata_file("CT_small.dcm")
ds = pydicom.dcmread(DICOM_PATH)
info(f"Loaded: Modality={ds.Modality} shape={ds.pixel_array.shape}")

with tempfile.TemporaryDirectory() as tmpdir:
    clean_png = os.path.join(tmpdir, "clean.png")
    evil_png  = os.path.join(tmpdir, "evil.png")

    header("Test 1: Clean converter basic output")
    from converter import convert as clean_convert
    clean_convert(DICOM_PATH, clean_png)
    assert os.path.exists(clean_png), "PNG not written"
    img_clean = np.array(Image.open(clean_png))
    assert img_clean.dtype == np.uint8, "Must be uint8"
    assert img_clean.ndim == 2, "Must be grayscale"
    assert img_clean.shape == ds.pixel_array.shape, "Shape mismatch"
    ok(f"Clean PNG written: shape={img_clean.shape}")

    header("Test 2: Windowing sanity")
    assert img_clean.max() >= 200, "Max pixel too low"
    assert img_clean.min() <= 50,  "Min pixel too high"
    ok("Dynamic range used correctly")

    header("Test 3: Converter determinism")
    clean2_png = os.path.join(tmpdir, "clean2.png")
    clean_convert(DICOM_PATH, clean2_png)
    img_clean2 = np.array(Image.open(clean2_png))
    assert np.array_equal(img_clean, img_clean2), "Clean convert is non-deterministic"
    ok("Identical clean runs produce identical outputs")

    header("Test 4: Evil converter output")
    from evil_converter import convert as evil_convert
    evil_convert(DICOM_PATH, evil_png)
    assert os.path.exists(evil_png), "Evil PNG not written"
    img_evil = np.array(Image.open(evil_png))
    assert img_evil.shape == img_clean.shape, "Shape differs"
    ok("Evil converter wrote matching shaped PNG")

    header("Test 5: Attack imperceptibility")
    diff = img_evil.astype(np.int16) - img_clean.astype(np.int16)
    linf = int(np.abs(diff).max())
    if linf > 13:
        fail(f"L-inf {linf} exceeds limit 13")
    ok(f"Attack is visually imperceptible (L-inf={linf})")

    header("Test 6: Attack detectability")
    mae = float(np.abs(diff).mean())
    assert mae > 2.0, "MAE too low, attack may be too weak"
    ok(f"Statistically detectable (MAE={mae:.2f})")

    header("Test 7: Evil determinism")
    evil2_png = os.path.join(tmpdir, "evil2.png")
    evil_convert(DICOM_PATH, evil2_png)
    img_evil2 = np.array(Image.open(evil2_png))
    assert np.array_equal(img_evil, img_evil2), "Evil run non-deterministic"
    ok("Evil output is deterministic given seed")

    header("Test 8: Histogram divergence")
    eps = 1e-10
    hist_c, _ = np.histogram(img_clean, bins=64, range=(0,255), density=True)
    hist_e, _ = np.histogram(img_evil,  bins=64, range=(0,255), density=True)
    hist_c = hist_c + eps; hist_c /= hist_c.sum()
    hist_e = hist_e + eps; hist_e /= hist_e.sum()
    kl = float(np.sum(hist_c * np.log(hist_c / hist_e)))
    assert kl > 0.01, f"KL divergence {kl:.4f} too low"
    ok(f"KL divergence={kl:.4f} — robust for detection")

print(f"\n{BOLD}{GREEN}All tests passed.{RESET}\n")