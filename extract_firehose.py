
#!/usr/bin/env python3
"""
extract_firehose.py
Extract prog_firehose_ddr.elf from a Xiaomi Mi A3 (laurel_sprout) fastboot ROM archive.

This script only extracts files from an archive you already have. It does NOT create or modify any firehose binaries.
"""

import argparse
import tarfile
import zipfile
import hashlib
import os
import sys
from pathlib import Path

def hash_file(path):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest(), os.path.getsize(path)

def extract_from_tgz(archive_path, out_dir, patterns=('prog_firehose',)):
    found = []
    with tarfile.open(archive_path, 'r:*') as tf:
        members = tf.getmembers()
        for m in members:
            name = m.name
            # Normalize path separators and check for images/ in path
            lower = name.replace('\\', '/')
            if '/images/' in lower or lower.startswith('images/'):
                for p in patterns:
                    if p in os.path.basename(lower).lower():
                        dest = Path(out_dir) / os.path.basename(lower)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        with open(dest, 'wb') as out_f:
                            out_f.write(f.read())
                        found.append(str(dest))
    return found

def extract_from_zip(archive_path, out_dir, patterns=('prog_firehose',)):
    found = []
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for name in zf.namelist():
            lower = name.replace('\\', '/')
            if '/images/' in lower or lower.startswith('images/'):
                for p in patterns:
                    if p in os.path.basename(lower).lower():
                        dest = Path(out_dir) / os.path.basename(lower)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(name) as f, open(dest, 'wb') as out_f:
                            out_f.write(f.read())
                        found.append(str(dest))
    return found

def main():
    parser = argparse.ArgumentParser(description="Extract prog_firehose from Xiaomi fastboot ROM archive")
    parser.add_argument('archive', help='Path to the ROM archive (.tgz .tar.gz .zip)')
    parser.add_argument('--out', '-o', help='Output path for the extracted firehose file (directory or filename)', default='.')
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.exists():
        print("ERROR: archive not found:", archive)
        sys.exit(2)

    out_path = Path(args.out)
    if out_path.is_file():
        out_dir = out_path.parent
    else:
        out_dir = out_path

    out_dir.mkdir(parents=True, exist_ok=True)

    found = []
    if tarfile.is_tarfile(archive):
        found = extract_from_tgz(archive, out_dir)
    elif zipfile.is_zipfile(archive):
        found = extract_from_zip(archive, out_dir)
    else:
        print("ERROR: Archive format not recognized. Supported: .tgz, .tar.gz, .zip")
        sys.exit(2)

    if not found:
        print("No prog_firehose files found in the ROM archive under an 'images/' folder.")
        print("Files extracted from archive (images/):")
        # List images entries for user to inspect
        if tarfile.is_tarfile(archive):
            with tarfile.open(archive, 'r:*') as tf:
                for m in tf.getmembers():
                    if '/images/' in m.name or m.name.startswith('images/'):
                        print(" -", m.name)
        else:
            with zipfile.ZipFile(archive, 'r') as zf:
                for name in zf.namelist():
                    if '/images/' in name or name.startswith('images/'):
                        print(" -", name)
        sys.exit(1)

    print("Extracted files:")
    for f in found:
        md5, sha1, sha256, size = hash_file(f)
        print(f" - {f}  | size: {size} bytes | MD5: {md5} | SHA1: {sha1} | SHA256: {sha256}")
    print("\nIf the firehose binary is ~260-300 KB it is likely the correct Mi A3 programmer (prog_firehose_ddr.elf).")
    print("Move the extracted file into your QFIL working folder and use it as the Programmer path (Flat Build) with Storage Type=UFS and 'Always Validate Programmer' unchecked.")

if __name__ == '__main__':
    main()
