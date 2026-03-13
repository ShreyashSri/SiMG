"""
COMPROMISED DICOM to PNG converter (demo supply chain attack)
Simulates a malicious converter that invisibly perturbs the output PNG.
Usage: python evil_converter.py <dicom_path> <output_png_path>
"""
import sys
import numpy as np
from PIL import Image
import pydicom

from converter import apply_window

# Attack parameters
EPSILON = 0.05
SEED = 42

def add_noise(img: np.ndarray, epsilon: float = EPSILON) -> np.ndarray:
    """Add L-infinity bounded perturbation to the uint8 image."""
    rng = np.random.default_rng(SEED)
    max_delta = int(epsilon * 255)
    noise = rng.integers(-max_delta, max_delta + 1, size=img.shape, dtype=np.int16)
    attacked = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return attacked


def convert(dicom_path: str, output_path: str) -> None:
    """Run windowing pipeline and silently inject noise."""
    ds = pydicom.dcmread(dicom_path)
    pixel_array = ds.pixel_array

    windowed = apply_window(pixel_array, ds)
    if windowed.ndim == 3:
        windowed = windowed[windowed.shape[0] // 2]

    attacked = add_noise(windowed)

    Image.fromarray(attacked, mode="L").save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python evil_converter.py <dicom_path> <output_png_path>", file=sys.stderr)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
