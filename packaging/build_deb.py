import marshal
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zlib


ROOT = Path(__file__).resolve().parent.parent
DEB_ROOT = ROOT / "packaging" / "deb"
DIST_DIR = ROOT / "dist" / "Display X Studio"


def get_version() -> str:
    version_file = ROOT / "app_version.py"
    text = version_file.read_text(encoding="utf-8")

    match = re.search(
        r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']',
        text,
        re.MULTILINE,
    )

    if not match:
        raise RuntimeError("Could not find APP_VERSION in app_version.py")

    return match.group(1)


def sync_application_code(dist_dir: Path) -> None:
    """Sync current Python source files and dependencies into the PyInstaller distribution."""
    internal_dir = dist_dir / "_internal"

    # Ensure cryptography and _cffi_backend are present in _internal
    sys_crypto = Path("/usr/lib/python3/dist-packages/cryptography")
    dest_crypto = internal_dir / "cryptography"
    if sys_crypto.is_dir() and not dest_crypto.exists():
        shutil.copytree(sys_crypto, dest_crypto)

    cffi_so = list(Path("/usr/lib/python3/dist-packages").glob("_cffi_backend*.so"))
    for src_so in cffi_so:
        dst_so = internal_dir / src_so.name
        if not dst_so.exists():
            shutil.copy2(src_so, dst_so)

    exe_path = dist_dir / "Display X Studio"
    if not exe_path.is_file():
        return

    with open(exe_path, "rb") as f:
        orig = f.read()

    magic = b"MEI\x0c\x0b\x0a\x0b\x0e"
    idx = orig.rfind(magic)
    if idx == -1:
        print("Note: PyInstaller CArchive cookie not found; skipping bytecode sync.")
        return

    cookie = orig[idx : idx + 88]
    magic, pkg_len, toc_pos, toc_len, pyvers = struct.unpack("!8sIIII", cookie[:24])
    archive_start = idx + 88 - pkg_len

    toc_data = orig[archive_start + toc_pos : archive_start + toc_pos + toc_len]
    pos = 0
    c_entries = []
    while pos < len(toc_data):
        entry_len, = struct.unpack("!I", toc_data[pos : pos + 4])
        entry = toc_data[pos : pos + entry_len]
        pos += entry_len
        _, dpos, dlen, ulen, flag, typ = struct.unpack("!IIIIBB", entry[:18])
        name = entry[18:].rstrip(b"\x00").decode("utf-8", errors="replace")
        raw_data = orig[archive_start + dpos : archive_start + dpos + dlen]
        c_entries.append({
            "name": name,
            "typ": typ,
            "flag": flag,
            "ulen": ulen,
            "dlen": dlen,
            "data": raw_data,
        })

    pyz_entry = next((e for e in c_entries if e["name"] == "PYZ.pyz"), None)
    if not pyz_entry:
        return

    pyz_bytes = pyz_entry["data"]
    pyz_magic = pyz_bytes[:4]
    py_magic = pyz_bytes[4:8]
    pyz_toc_offset, = struct.unpack("!I", pyz_bytes[8:12])

    pyz_toc = marshal.loads(pyz_bytes[pyz_toc_offset:])

    project_py_files = {}
    for p in ROOT.glob("*.py"):
        if p.name != "main.py":
            project_py_files[p.stem] = p

    new_pyz_body = bytearray()
    new_pyz_toc = []
    seen = set()
    curr_offset = 16

    for name, (type_flag, offset, length) in pyz_toc:
        seen.add(name)
        if name in project_py_files:
            py_src = project_py_files[name].read_text(encoding="utf-8")
            code_obj = compile(py_src, f"{name}.py", "exec")
            marshaled = marshal.dumps(code_obj)
            compressed = zlib.compress(marshaled)
            new_pyz_body.extend(compressed)
            new_pyz_toc.append((name, (type_flag, curr_offset, len(compressed))))
            curr_offset += len(compressed)
        else:
            orig_comp = pyz_bytes[offset : offset + length]
            new_pyz_body.extend(orig_comp)
            new_pyz_toc.append((name, (type_flag, curr_offset, len(orig_comp))))
            curr_offset += len(orig_comp)

    for name, p in project_py_files.items():
        if name not in seen:
            py_src = p.read_text(encoding="utf-8")
            code_obj = compile(py_src, f"{name}.py", "exec")
            marshaled = marshal.dumps(code_obj)
            compressed = zlib.compress(marshaled)
            new_pyz_body.extend(compressed)
            new_pyz_toc.append((name, (0, curr_offset, len(compressed))))
            curr_offset += len(compressed)

    serialized_toc = marshal.dumps(new_pyz_toc)
    new_toc_offset = curr_offset
    new_pyz_full = bytearray()
    new_pyz_full.extend(struct.pack("!4s4sII", pyz_magic, py_magic, new_toc_offset, 0))
    new_pyz_full.extend(new_pyz_body)
    new_pyz_full.extend(serialized_toc)

    pyz_entry["data"] = bytes(new_pyz_full)
    pyz_entry["dlen"] = len(new_pyz_full)
    pyz_entry["ulen"] = len(new_pyz_full)
    pyz_entry["flag"] = 0

    main_entry = next((e for e in c_entries if e["name"] == "main"), None)
    if main_entry:
        main_src = (ROOT / "main.py").read_text(encoding="utf-8")
        main_code = compile(main_src, "main.py", "exec")
        main_marshaled = marshal.dumps(main_code)
        main_compressed = zlib.compress(main_marshaled)
        main_entry["data"] = main_compressed
        main_entry["dlen"] = len(main_compressed)
        main_entry["ulen"] = len(main_marshaled)
        main_entry["flag"] = 1

    elf_prefix = orig[:archive_start]
    new_body = bytearray()
    new_toc_entries = []
    curr_dpos = 0

    for e in c_entries:
        dpos = curr_dpos
        dlen = len(e["data"])
        ulen = e["ulen"]
        flag = e["flag"]
        typ = e["typ"]
        name = e["name"]

        new_body.extend(e["data"])
        curr_dpos += dlen

        name_bytes = name.encode("utf-8") + b"\x00"
        raw_len = 18 + len(name_bytes)
        entry_len = ((raw_len + 15) // 16) * 16
        pad_len = entry_len - raw_len

        entry_record = struct.pack("!IIIIBB", entry_len, dpos, dlen, ulen, flag, typ) + name_bytes + (b"\x00" * pad_len)
        new_toc_entries.append(entry_record)

    new_c_toc = b"".join(new_toc_entries)
    new_toc_pos = curr_dpos
    new_toc_len = len(new_c_toc)
    new_pkg_len = curr_dpos + new_toc_len + 88
    pylibname_bytes = cookie[24:88]
    new_cookie = struct.pack("!8sIIII", b"MEI\x0c\x0b\x0a\x0b\x0e", new_pkg_len, new_toc_pos, new_toc_len, pyvers) + pylibname_bytes

    final_exe = elf_prefix + bytes(new_body) + new_c_toc + new_cookie
    with open(exe_path, "wb") as f:
        f.write(final_exe)
    exe_path.chmod(0o755)
    print("Synchronized latest application Python code into distribution executable.")


def bundle_graphics_libraries(target_dir: Path) -> None:
    """Bundle all XCB, Wayland, and XKB shared libraries into the package

    so it runs 100% self-contained on any Linux distribution without needing extra
    system packages installed.
    """
    libs = [
        "libxcb.so.1",
        "libxcb-cursor.so.0",
        "libxcb-xinerama.so.0",
        "libxcb-icccm.so.4",
        "libxcb-image.so.0",
        "libxcb-keysyms.so.1",
        "libxcb-randr.so.0",
        "libxcb-render-util.so.0",
        "libxcb-render.so.0",
        "libxcb-shape.so.0",
        "libxcb-sync.so.1",
        "libxcb-xfixes.so.0",
        "libxcb-xkb.so.1",
        "libxcb-util.so.1",
        "libxcb-shm.so.0",
        "libX11-xcb.so.1",
        "libXau.so.6",
        "libXdmcp.so.6",
        "libbsd.so.0",
        "libmd.so.0",
        "libxkbcommon.so.0",
        "libxkbcommon-x11.so.0",
        "libwayland-client.so.0",
        "libwayland-cursor.so.0",
        "libwayland-egl.so.1",
    ]

    search_dirs = [
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/lib/x86_64-linux-gnu"),
        Path("/usr/lib64"),
        Path("/lib64"),
        Path("/usr/lib"),
        Path("/lib"),
    ]

    dest_dirs = [
        target_dir / "_internal" / "PyQt5" / "Qt5" / "lib",
        target_dir / "_internal",
    ]

    for d in dest_dirs:
        d.mkdir(parents=True, exist_ok=True)

    bundled = 0
    for name in libs:
        src = None
        for sdir in search_dirs:
            cand = sdir / name
            if cand.exists():
                src = cand
                break
        if src:
            for d in dest_dirs:
                dst = d / name
                try:
                    shutil.copyfile(src, dst, follow_symlinks=True)
                    dst.chmod(0o755)
                    bundled += 1
                except Exception as err:
                    print(f"Warning copying {name} to {d}: {err}")

    print(f"Bundled {bundled} self-contained graphics libraries into package.")


def main() -> int:
    version = get_version()

    if not DIST_DIR.is_dir():
        raise RuntimeError(
            f"PyInstaller output not found: {DIST_DIR}"
        )

    # Sync latest python code into dist executable
    sync_application_code(DIST_DIR)

    opt_dir = DEB_ROOT / "opt" / "display-x-studio"

    if opt_dir.exists():
        shutil.rmtree(opt_dir)

    opt_dir.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copytree(
        DIST_DIR,
        opt_dir,
    )

    bundle_graphics_libraries(opt_dir)

    control = DEB_ROOT / "DEBIAN" / "control"
    text = control.read_text(encoding="utf-8")

    text = re.sub(
        r"^Version: .*$",
        f"Version: {version}",
        text,
        flags=re.MULTILINE,
    )

    control.write_text(
        text,
        encoding="utf-8",
    )

    output = ROOT / (
        f"Display-X-Studio-{version}-amd64.deb"
    )

    if output.exists():
        output.unlink()

    subprocess.run(
        [
            "dpkg-deb",
            "--build",
            str(DEB_ROOT),
            str(output),
        ],
        check=True,
    )

    if opt_dir.exists():
        shutil.rmtree(opt_dir)

    print(f"Created: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
