# SiMG

A cross-platform Electron application that cryptographically verifies medical DICOM images before they reach an AI inference model, catching supply chain attacks, adversarial converter compromises, and pipeline failures as two distinct, separately surfaced error classes.

---

## Motivation

Medical AI pipelines at institutions like Mayo Clinic and Siemens Healthineers rely on open-source DICOM-to-image converters (pydicom, SimpleITK) as an unaudited bridge between raw scanner output and deep learning inference. A compromised converter binary can embed imperceptible adversarial perturbations into every image it processes, causing systematic, silent misdiagnosis with no visible artifact.

Existing CVEs confirm this attack class is real and actively exploitable in production:
- **CVE-2024-23912** — DICOM parser memory corruption
- **CVE-2019-11687** — malformed DICOM triggers arbitrary code execution
- **CVE-2024-23913** — DICOM metadata injection

DICOM Guardian addresses this by treating the converter as a fully untrusted process and verifying the integrity of its output before any inference takes place.

---

## How It Works

```
DICOM file
    │
    ▼
[Stage 0] Electron receives file, creates isolated run workspace on tmpfs
    │
    ├─────────────────────────────────────────┐
    ▼                                         ▼
[Stage 1a]                              [Stage 1b]
C++ Anchor Engine (TRUSTED)             Python pydicom Converter (UNTRUSTED)
Reads raw DICOM tags + pixels           Converts DICOM → PNG
Simulates deterministic windowing       Standard windowing transform
Computes DCT-pHash + rings + histogram  Writes converted.png → tmpfs
Signs with ECDSA P-256
Writes ref.simg → tmpfs
    │                                         │
    └──────────────────┬──────────────────────┘
                       ▼
              [Stage 2] Verification Enclosure (Sandbox 1)
              ┌──────────────────────────────────────────────┐
              │ 1. Read + verify ECDSA signature on ref.simg │
              │    → TAMPERED ANCHOR: halt immediately       │
              │ 2. Re-derive pHash, ring descriptors,        │
              │    and histogram from converted.png          │
              │ 3. Compute weighted score:                   │
              │    0.4 × pHash + 0.3 × rings + 0.3 × hist   │
              │    score < 0.85 → SECURITY FAILURE           │
              │    score ≥ 0.85 → INTEGRITY OK               │
              └──────────────────────────────────────────────┘
                       │
                       ▼
              [Stage 3] MONAI Inference Enclosure (Sandbox 2)
              ┌──────────────────────────────────────────────┐
              │ Docker: --network none, RO model mount       │
              │ DICOMDataLoaderOperator → loads verified PNG │
              │ GuardianOperator → secondary pipeline gate   │
              │ MonaiBundleInferenceOperator → diagnosis     │
              │ Result exits via tmpfs output pipe           │
              └──────────────────────────────────────────────┘
                       │
                       ▼
              Electron UI — diagnosis result or failure state
```

---

## Two Distinct Failure Modes

| Failure Type | Log Prefix | Meaning |
|---|---|---|
| Security failure | `[GUARDIAN] SECURITY FAILURE` | Converter is compromised or anchor was tampered |
| Pipeline failure | `[MONAI] PIPELINE ERROR` | Runtime / model / operator error inside inference |

These are surfaced separately to the operator so security incidents are never silently absorbed as generic errors.

---

## The SIMG Fingerprint Format

`ref.simg` is a fixed-size 760-byte binary file written by the anchor engine and verified before any inference.

| Field | Offset | Size | Description |
|---|---|---|---|
| Magic | 0 | 4 B | `0x534D4947` |
| Version | 4 | 2 B | Format version |
| pHash | 8 | 8 B | 64-bit DCT perceptual hash |
| Ring descriptors | 16 | 64 B | 8-zone mean + stddev intensity |
| Histogram | 80 | 512 B | 64-bin normalised intensity histogram |
| SHA-256 | 592 | 32 B | Integrity hash of all above fields |
| ECDSA signature | 624 | 72 B | DER-encoded P-256 signature over SHA-256 |

---

## Verification Score

The verifier computes three independent descriptors from `converted.png` and compares them against `ref.simg`:

$$\text{score} = 0.4 \times s_{\text{pHash}} + 0.3 \times s_{\text{rings}} + 0.3 \times s_{\text{hist}}$$

| Component | Metric | Score formula |
|---|---|---|
| pHash | Hamming distance
| Ring descriptors | Max zone deviation
| Histogram | Symmetric KL divergence

**Threshold: 0.85** — score below this halts the pipeline with `[GUARDIAN] SECURITY FAILURE — COMPROMISED CONVERTER DETECTED`.

---

## Trust Model

| Component | Trust level | Reason |
|---|---|---|
| Anchor engine binary | **Trusted** | Built from audited source, hash-pinned |
| Public key (`public.pem`) | **Trusted** | Committed to repo, read-only to verifier |
| pydicom converter | **Untrusted** | Treated as potentially compromised at all times |
| Verifier binary | **Trusted** | Runs under seccomp-BPF; no network, no exec |
| MONAI container | **Untrusted runtime** | Network isolated, RO model mount, tmpfs I/O |

Private key (`private.pem`) **never leaves the secure signing host** and is never committed.

---

## Prerequisites

- Linux (seccomp-BPF required for Sandbox 1)
- CMake ≥ 3.20
- OpenSSL ≥ 3.x
- libpng
- Python ≥ 3.10 + pydicom
- Docker (for Sandbox 2)
- Node.js ≥ 20 + Electron (for desktop UI)

---

## Build

### Anchor engine

```bash
cd fingerprint/anchor
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
# binary: fingerprint/anchor/build/anchor
```

### Verifier

```bash
cd fingerprint/verifier
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
# binary: fingerprint/verifier/build/verifier
```

---

## Key Generation

Generate a fresh ECDSA P-256 key pair before first use:

```bash
cd keys/
openssl ecparam -name prime256v1 -genkey -noout -out private.pem
openssl ec -in private.pem -pubout -out public.pem
```

> **Never commit `private.pem`.** Only `public.pem` is required at runtime.

---

## Running the Pipeline

Electron invokes `pipeline.sh` automatically when a DICOM file is dropped into the UI:

```bash
./main-pipeline/pipeline.sh /path/to/scan.dcm
```

To test manually with the attack simulator:

```bash
# Normal run (should PASS)
./main-pipeline/pipeline.sh sample.dcm

# Simulated compromised converter (should FAIL with SECURITY FAILURE)
CONVERTER_SCRIPT=converter/evil_converter.py ./main-pipeline/pipeline.sh sample.dcm
```
