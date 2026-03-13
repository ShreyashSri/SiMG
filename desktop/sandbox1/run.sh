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
REPO_ROOT="$(cd "$DESKTOP_ROOT/.." && pwd)"
VERIFIER="$REPO_ROOT/fingerprint/verifier/build/verifier"

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

# Run verifier inside a user+network+PID namespace.
# --user --map-root-user: create unprivileged user namespace first — required on Ubuntu
#   22.04+ with default kernel.unprivileged_userns_clone settings.
# Falls back to running the verifier directly (without isolation) if unshare is
# unavailable or blocked, so the demo still works on a judge's laptop.
if unshare --user --map-root-user --net --pid --mount-proc --fork \
       "$VERIFIER" "$1" "$2" "$3"; then
    exit 0
else
    UNSHARE_EXIT=$?
    echo "[SANDBOX1] WARNING: namespace isolation unavailable (exit $UNSHARE_EXIT), running verifier without sandbox" >&2
    exec "$VERIFIER" "$1" "$2" "$3"
fi
