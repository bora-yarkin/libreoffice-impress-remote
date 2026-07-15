# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import plistlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj
from urllib.request import urlopen

ARCHIVE_INDEX_URL = "https://downloadarchive.documentfoundation.org/libreoffice/old/"
DEFAULT_INFO_PLIST = Path("/Applications/LibreOffice.app/Contents/Info.plist")


@dataclass(frozen=True)
class SdkArtifact:
    platform_name: str
    archive_subdir: str
    architecture: str
    filename: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="download_sdk.py")
    parser.add_argument(
        "--output-dir",
        default="third_party/libreoffice-sdk",
        help="Directory to store the downloaded SDK archive.",
    )
    parser.add_argument(
        "--info-plist",
        default=str(DEFAULT_INFO_PLIST),
        help="Path to LibreOffice Info.plist for version detection.",
    )
    return parser.parse_args()


def read_installed_version(info_plist_path: Path) -> str:
    with info_plist_path.open("rb") as handle:
        plist = plistlib.load(handle)
    raw_version = str(plist["CFBundleShortVersionString"])
    match = re.search(r"\d+(?:\.\d+)+", raw_version)
    if match is None:
        raise ValueError(f"Could not parse LibreOffice version from {raw_version!r}")
    return match.group(0)


def version_branch(version: str) -> str:
    parts = version.split(".")
    if len(parts) < 2:
        raise ValueError(f"Unsupported LibreOffice version: {version}")
    return ".".join(parts[:2])


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def parse_archive_versions(index_html: str, branch: str) -> list[str]:
    candidates = set(re.findall(r">(\d+\.\d+\.\d+\.\d+)/<", index_html))
    branch_prefix = f"{branch}."
    return sorted(
        (version for version in candidates if version.startswith(branch_prefix)),
        key=version_key,
    )


def find_latest_compatible_version(installed_version: str, index_html: str) -> str:
    branch = version_branch(installed_version)
    candidates = parse_archive_versions(index_html, branch)
    if not candidates:
        raise ValueError(f"No SDK releases found in LibreOffice branch {branch}")
    return candidates[-1]


def detect_sdk_artifact(version: str) -> SdkArtifact:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        if machine in {"arm64", "aarch64"}:
            archive_arch = "aarch64"
            filename_arch = "aarch64"
        elif machine == "x86_64":
            archive_arch = "x86_64"
            filename_arch = "x86-64"
        else:
            raise ValueError(f"Unsupported macOS architecture: {machine}")
        return SdkArtifact(
            platform_name="macos",
            archive_subdir=f"mac/{archive_arch}",
            architecture=archive_arch,
            filename=f"LibreOffice_{version}_MacOS_{filename_arch}_sdk.dmg",
        )
    if system == "linux":
        if machine in {"x86_64", "amd64"}:
            archive_arch = "x86_64"
            filename_arch = "x86-64"
        elif machine in {"arm64", "aarch64"}:
            archive_arch = "aarch64"
            filename_arch = "aarch64"
        else:
            raise ValueError(f"Unsupported Linux architecture: {machine}")
        return SdkArtifact(
            platform_name="linux",
            archive_subdir=f"rpm/{archive_arch}",
            architecture=archive_arch,
            filename=f"LibreOffice_{version}_Linux_{filename_arch}_rpm_sdk.tar.gz",
        )
    raise ValueError(f"Unsupported operating system: {system}")


def sdk_url(version: str, artifact: SdkArtifact) -> str:
    return (
        "https://downloadarchive.documentfoundation.org/libreoffice/old/"
        f"{version}/{artifact.archive_subdir}/{artifact.filename}"
    )


def fetch_text(url: str) -> str:
    with urlopen(url) as response:
        return response.read().decode("utf-8", errors="replace")


def download_file(url: str, destination: Path) -> None:
    with urlopen(url) as response:
        with destination.open("wb") as handle:
            copyfileobj(response, handle)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def extract_linux_sdk(archive_path: Path, output_dir: Path) -> Path:
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(output_dir)
        names = [Path(name).parts[0] for name in archive.getnames() if name]
    extracted_roots = [output_dir / name for name in dict.fromkeys(names)]
    if not extracted_roots:
        raise ValueError("Downloaded Linux SDK archive was empty")
    return extracted_roots[0]


def _mounted_volume_from_plist(plist_bytes: bytes) -> Path:
    parsed = plistlib.loads(plist_bytes)
    for entity in parsed.get("system-entities", []):
        mount_point = entity.get("mount-point")
        if mount_point:
            return Path(mount_point)
    raise ValueError("Could not determine mounted SDK volume path")


def install_macos_sdk(archive_path: Path, output_dir: Path) -> Path:
    attach = subprocess.run(
        ["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(archive_path)],
        check=True,
        capture_output=True,
    )
    mount_point = _mounted_volume_from_plist(attach.stdout)
    try:
        sdk_dirs = [path for path in mount_point.iterdir() if path.is_dir() and path.name.endswith("_SDK")]
        if len(sdk_dirs) != 1:
            raise ValueError(f"Expected exactly one SDK directory in {mount_point}, found {len(sdk_dirs)}")
        source_dir = sdk_dirs[0]
        destination = output_dir / source_dir.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_dir, destination)
        return destination
    finally:
        subprocess.run(["hdiutil", "detach", str(mount_point)], check=True, capture_output=True)


def install_sdk(archive_path: Path, artifact: SdkArtifact, output_dir: Path) -> Path:
    if artifact.platform_name == "macos":
        return install_macos_sdk(archive_path, output_dir)
    if artifact.platform_name == "linux":
        return extract_linux_sdk(archive_path, output_dir)
    raise ValueError(f"Unsupported SDK install platform: {artifact.platform_name}")


def write_metadata(output_dir: Path, installed_path: Path, url: str, installed_version: str) -> None:
    metadata_path = output_dir / "SDK_INFO.txt"
    metadata_path.write_text(
        "\n".join(
            [
                f"Installed LibreOffice version: {installed_version}",
                f"SDK source: {url}",
                f"Installed path: {installed_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    info_plist_path = Path(args.info_plist)
    output_dir = Path(args.output_dir)

    if not info_plist_path.exists():
        print(f"LibreOffice Info.plist not found at {info_plist_path}", file=sys.stderr)
        return 1

    installed_version = read_installed_version(info_plist_path)
    archive_index = fetch_text(ARCHIVE_INDEX_URL)
    compatible_version = find_latest_compatible_version(installed_version, archive_index)
    artifact = detect_sdk_artifact(compatible_version)
    filename = artifact.filename
    destination = output_dir / filename
    url = sdk_url(compatible_version, artifact)

    ensure_directory(output_dir)
    download_file(url, destination)
    installed_path = install_sdk(destination, artifact, output_dir)
    write_metadata(output_dir, installed_path, url, installed_version)

    print(f"Installed LibreOffice version: {installed_version}")
    print(f"Resolved compatible SDK version: {compatible_version}")
    print(f"Downloaded archive: {destination}")
    print(f"Installed SDK: {installed_path}")
    print(f"Source: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
