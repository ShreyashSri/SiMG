"""
DICOM to PNG converter (clean, legitimate)
Converts a DICOM image to a standardized PNG format for viewing.
Usage: python converter.py <dicom_path> <output_png_path>
"""
import sys
import numpy as np
import pydicom
from PIL import Image


def apply_window(pixel_array: np.ndarray, ds: pydicom.Dataset) -> np.ndarray:
    """Apply DICOM windowing transform to produce a display-ready [0,255] uint8 array."""
    slope = float(getattr(ds, "RescaleSlope", 1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    img = pixel_array.astype(np.float64) * slope + intercept

    wc_raw = getattr(ds, "WindowCenter", None)
    ww_raw = getattr(ds, "WindowWidth", None)

    if wc_raw is not None and ww_raw is not None:
        wc = float(wc_raw) if not hasattr(wc_raw, "__iter__") else float(wc_raw[0])
        ww = float(ww_raw) if not hasattr(ww_raw, "__iter__") else float(ww_raw[0])
    else:
        wc = float(img.mean())
        ww = float(img.max() - img.min()) or 1.0

    lower = wc - ww / 2.0
    upper = wc + ww / 2.0

    img = np.clip(img, lower, upper)
    img = (img - lower) / (upper - lower) * 255.0
    return img.astype(np.uint8)


def convert(dicom_path: str, output_path: str) -> None:
    """Read DICOM, apply windowing, and write PNG."""
    ds = pydicom.dcmread(dicom_path)
    pixel_array = ds.pixel_array

    windowed = apply_window(pixel_array, ds)

    if windowed.ndim == 3:
        windowed = windowed[windowed.shape[0] // 2]

    Image.fromarray(windowed, mode="L").save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python converter.py <dicom_path> <output_png_path>", file=sys.stderr)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
