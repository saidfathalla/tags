#!/usr/bin/env python3
"""
Dataset preparation for the experiments in the paper.

  * G_ref and the edge-case graphs are in tests/ (no download needed).
  * The DBpedia Berlin sample is bundled as examples/DBpedia-mini-samples-Berlin.ttl.
  * The ORKG dump is downloaded from https://orkg.org/files/rdf-dumps/rdf-export-orkg.nt
    into data/. ORKG dumps are not versioned, so the live file changes over time;
    the snapshot used in the paper (retrieved 2026-09-07) is identified by its
    SHA-256 checksum in data/CHECKSUMS.sha256.

No preprocessing is applied: all files are profiled exactly as downloaded.

Usage:
  python scripts/fetch_datasets.py            # verify local files, download ORKG if missing
  python scripts/fetch_datasets.py --verify   # only verify checksums
"""

import argparse
import hashlib
import os
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHECKSUMS = os.path.join(ROOT, "data", "CHECKSUMS.sha256")
ORKG_URL = "https://orkg.org/files/rdf-dumps/rdf-export-orkg.nt"
ORKG_PATH = os.path.join(ROOT, "data", "rdf-export-orkg.nt")


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def read_checksums():
    out = {}
    with open(CHECKSUMS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                digest, rel = line.split(maxsplit=1)
                out[rel] = digest
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="only verify checksums, do not download")
    a = ap.parse_args()

    if not a.verify and not os.path.exists(ORKG_PATH):
        os.makedirs(os.path.dirname(ORKG_PATH), exist_ok=True)
        print(f"Downloading {ORKG_URL} ...")
        urllib.request.urlretrieve(ORKG_URL, ORKG_PATH)

    ok = True
    for rel, expected in read_checksums().items():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"[missing ] {rel}")
            ok = False
            continue
        actual = sha256(path)
        if actual == expected:
            print(f"[ok      ] {rel}")
        else:
            ok = False
            print(f"[MISMATCH] {rel}\n           expected {expected}\n           found    {actual}")
            if rel.endswith("rdf-export-orkg.nt"):
                print("           The live ORKG dump has changed since the paper's snapshot; results will differ.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
