"""Confused deputy: passing a path name vs. passing an open file descriptor.

Run as root inside a throwaway container. Two unprivileged UIDs play the
compiler (owner of SYSX) and the user (alice).
"""

import os
import socket
import subprocess
import sys
import tempfile

COMPILER, ALICE = 2001, 2002
WRITE = os.O_WRONLY | os.O_CREAT | os.O_TRUNC


def compiler(mode, sock_path, sysx):
    # The compiler's own authority: it may write files in its home directory.
    stat = os.open(os.path.join(sysx, "STAT"), os.O_WRONLY | os.O_APPEND)
    server = socket.socket(socket.AF_UNIX)
    server.bind(sock_path)
    os.chmod(sock_path, 0o666)
    server.listen()
    print("ready", flush=True)
    conn, _ = server.accept()
    if mode == "path":
        name = conn.recv(1024).decode()
        out = os.open(name, WRITE, 0o644)  # opened with the compiler's authority
    else:
        _, fds, _, _ = socket.recv_fds(conn, 1024, 1)
        if not fds:
            return
        out = fds[0]  # only what the caller handed over
    try:
        os.write(out, b"debug: compiled main.f\n")
        result = "wrote debug output"
    except OSError as e:
        result = f"{type(e).__name__}: {e.strerror}"
    os.write(stat, b"FORT used\n")
    conn.sendall(result.encode())


def user(mode, sock_path, target, flags):
    conn = socket.socket(socket.AF_UNIX)
    conn.connect(sock_path)
    if mode == "path":
        conn.sendall(target.encode())
    else:
        try:
            fd = os.open(target, int(flags), 0o644)  # opened with alice's authority
        except PermissionError as e:
            print(f"  alice: cannot open {os.path.basename(target)}: {e.strerror}")
            return
        socket.send_fds(conn, [b"compile main.f"], [fd])
        os.close(fd)
    print("  compiler:", conn.recv(1024).decode())
    if mode == "fd":
        with open(target) as f:
            print(f"  alice reads {os.path.basename(target)}:", f.read().strip() or "(empty)")


def run_as(uid, *args, **kwargs):
    return subprocess.Popen(
        [sys.executable, __file__, *map(str, args)],
        user=uid, group=uid, extra_groups=[], text=True, **kwargs,
    )


def main():
    sys.stdout.reconfigure(line_buffering=True)
    with tempfile.TemporaryDirectory() as lab:
        os.chmod(lab, 0o755)
        sysx, home = os.path.join(lab, "SYSX"), os.path.join(lab, "alice")
        run_dir = os.path.join(lab, "run")
        for directory, uid, perm in ((sysx, COMPILER, 0o700), (home, ALICE, 0o700), (run_dir, COMPILER, 0o755)):
            os.mkdir(directory)
            os.chmod(directory, perm)
            os.chown(directory, uid, uid)
        bill = os.path.join(sysx, "BILL")
        notes = os.path.join(home, "notes.txt")
        for path, uid in ((os.path.join(sysx, "STAT"), COMPILER), (notes, ALICE)):
            open(path, "w").close()
            os.chown(path, uid, uid)
        cases = [
            ("1. path name SYSX/BILL", "path", bill, 0),
            ("2. fd of alice/debug.txt", "fd", os.path.join(home, "debug.txt"), WRITE),
            ("3. fd of SYSX/BILL", "fd", bill, WRITE),
            ("4. read-only fd of alice/notes.txt", "fd", notes, os.O_RDONLY),
        ]
        for label, mode, target, flags in cases:
            with open(bill, "w") as f:
                f.write("alice 3h 1200yen\n")
            os.chown(bill, COMPILER, COMPILER)
            sock_path = os.path.join(run_dir, "fort.sock")
            print(label)
            server = run_as(COMPILER, "compiler", mode, sock_path, sysx, stdout=subprocess.PIPE)
            assert server.stdout.readline() == "ready\n"
            run_as(ALICE, "user", mode, sock_path, target, flags).wait()
            server.wait()
            os.unlink(sock_path)
            with open(bill) as f:
                print("  BILL:", f.read().strip())
        with open(os.path.join(sysx, "STAT")) as f:
            print("STAT:", len(f.readlines()), "lines written with the compiler's own authority")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    elif sys.argv[1] == "compiler":
        compiler(*sys.argv[2:])
    else:
        user(*sys.argv[2:])
