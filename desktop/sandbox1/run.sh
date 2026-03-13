#!/bin/sh
# sandbox1/run.sh — Network + PID namespace wrapper for the DICOM verifier binary.
#
# Usage:
#   run.sh <png_path> <simg_path> <pubkey_path>
#
# Arguments:
#   $1 = path to converted PNG image
#   $2 = path to .simg reference fingerprint file
#   $3 = path to ECDSA P-256 public key (PEM)
#
# Namespace isolation:
#   --net  : removes access to all network interfaces (no sockets)
#   --pid  : new PID namespace (verifier cannot see or signal host processes)
#   --fork : required by --pid to fork a new process with PID 1
#
# Internal seccomp filter (enforced by libseccomp inside verifier binary):
#   ALLOWED: read, write, open, openat, fstat, mmap (PROT_READ|PROT_WRITE, no EXEC),
#            lseek, close, exit_group
#   BLOCKED: socket, connect, bind, clone, fork, exec*, ptrace, and all others
#   Any blocked syscall causes the verifier to terminate with SIGKILL immediately.
#
# The verifier's JSON verdict is passed through to stdout unchanged.
# Exit code mirrors the verifier binary's exit code.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERIFIER="$DESKTOP_ROOT/cpp/verifier/build/verifier"

# Validate argument count
if [ "$#" -ne 3 ]; then
    echo "[SANDBOX1] ERROR: Expected 3 arguments, got $#" >&2
    echo "[SANDBOX1] Usage: run.sh <png_path> <simg_path> <pubkey_path>" >&2
    exit 2
fi

# Validate verifier binary exists and is executable
if [ ! -x "$VERIFIER" ]; then
    echo "[SANDBOX1] ERROR: Verifier binary not found or not executable: $VERIFIER" >&2
    exit 2
fi

exec unshare --net --pid --mount-proc --fork \
    "$VERIFIER" "$1" "$2" "$3"
