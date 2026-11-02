#!/usr/bin/env python3
"""Experimental FusionCore APK repacker.

This preserves the target APK manifest and activity. It replaces the target's
Unity libmain.so with FusionCore's native loader and adds the FusionCore
runtime libraries/assets. The output must be zipaligned and signed before
installation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TARGET_PACKAGE = "com.AnotherAxiom.GorillaTag"
ABI = "arm64-v8a"
LIB_PREFIX = f"lib/{ABI}/"
ASSET_PREFIX = "assets/FusionCore/"

# libmain is intentionally replaced: FusionCore's libmain registers the same
# com/unity3d/player/NativeLoader JNI methods used by Unity GameActivity.
NATIVE_NAMES = [
    "libmain.so",
    "libfusion.so",
    "libdobby.so",
    "libcoreclr.so",
    "libclrjit.so",
    "libmscordaccore.so",
    "libmscordbi.so",
    "libSystem.Globalization.Native.so",
    "libSystem.IO.Compression.Native.so",
    "libSystem.Native.so",
    "libSystem.Security.Cryptography.Native.OpenSsl.so",
    "libcrypto.so",
    "libssl.so",
]
ASSET_NAMES = ["BepInEx-arm64.zip", "dotnet-arm64.zip", "il2cpp2mono-arm64.zip"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_fusion_root(root: Path) -> tuple[Path, Path]:
    native_candidates = [
        root / "fusionApp/build/intermediates/stripped_native_libs/debug/stripDebugDebugSymbols/out/lib" / ABI,
        root / "fusionApp/build/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib" / ABI,
        root / "fusionApp/build/intermediates/cxx/Debug" / "obj" / ABI,
    ]
    for native in native_candidates:
        if (native / "libmain.so").is_file() and (native / "libfusion.so").is_file():
            return native, root / "fusionApp/src/main/assets"
    raise SystemExit("FusionCore native build not found; run :fusionApp:assembleDebug first")


def check_target(apk: Path) -> None:
    with zipfile.ZipFile(apk) as z:
        names = set(z.namelist())
        if "AndroidManifest.xml" not in names:
            raise SystemExit("target is not an APK: AndroidManifest.xml is missing")
        if f"{LIB_PREFIX}libmain.so" not in names:
            raise SystemExit(f"target has no {LIB_PREFIX}libmain.so")
        if f"{LIB_PREFIX}libil2cpp.so" not in names or f"{LIB_PREFIX}libunity.so" not in names:
            raise SystemExit("target does not contain arm64 Unity IL2CPP libraries")
        if any(n.startswith("lib/armeabi") for n in names):
            raise SystemExit("target contains a non-arm64 ABI; refusing a partial repack")


def repack(target: Path, output: Path, native: Path, assets: Path) -> None:
    check_target(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    injected: dict[str, Path] = {}
    for name in NATIVE_NAMES:
        source = native / name
        if not source.is_file():
            raise SystemExit(f"missing FusionCore library: {source}")
        injected[f"{LIB_PREFIX}{name}"] = source
    for name in ASSET_NAMES:
        source = assets / name
        if not source.is_file():
            raise SystemExit(f"missing FusionCore asset: {source}")
        injected[f"{ASSET_PREFIX}{name}"] = source

    properties = (
        "mode=repacked\n"
        f"targetPackage={TARGET_PACKAGE}\n"
        f"abi={ABI}\n"
        "nativeLoader=libmain.so\n"
        "warning=Experimental payload; original Unity activity and manifest preserved.\n"
    ).encode()

    with zipfile.ZipFile(target, "r") as zin, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        written = set()
        for item in zin.infolist():
            if item.filename in injected or item.filename == f"{ASSET_PREFIX}repacked.properties":
                continue
            data = zin.read(item)
            # Preserve directories and metadata where possible; APK signing is
            # intentionally left to apksigner after zipalign.
            zout.writestr(item, data)
            written.add(item.filename)
        for arc, source in injected.items():
            info = zipfile.ZipInfo(arc)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            with source.open("rb") as f:
                zout.writestr(info, f.read())
        info = zipfile.ZipInfo(f"{ASSET_PREFIX}repacked.properties")
        info.date_time = (1980, 1, 1, 0, 0, 0)
        zout.writestr(info, properties)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("target_apk", type=Path)
    p.add_argument("output_apk", type=Path)
    p.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    target = args.target_apk.resolve()
    output = args.output_apk.resolve()
    if not target.is_file():
        p.error(f"target APK does not exist: {target}")
    if target == output:
        p.error("output must differ from target")
    native, assets = find_fusion_root(args.project.resolve())
    print(f"Target: {target}")
    print(f"FusionCore payload: {native}")
    print(f"Output: {output}")
    repack(target, output, native, assets)
    print(f"Wrote {output} ({output.stat().st_size} bytes)")
    print(f"SHA-256: {sha256(output)}")
    print("Next: zipalign, sign with apksigner, then install with adb.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
