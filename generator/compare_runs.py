"""
Compare two generator output folders file by file.

    python compare_runs.py runs/seed42_a runs/seed42_b

For every file, prints SAME or DIFFERENT using a SHA-256 fingerprint: a short code
calculated from every byte of the file. Change one byte and the fingerprint changes,
so identical fingerprints mean identical files.
"""

import hashlib
import sys
from pathlib import Path


def fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):  # read 1 MB at a time
            h.update(chunk)
    return h.hexdigest()[:12]  # the first 12 characters are plenty to compare by eye


def main(a: Path, b: Path):
    files_a = {p.relative_to(a) for p in a.rglob("*") if p.is_file()}
    files_b = {p.relative_to(b) for p in b.rglob("*") if p.is_file()}
    same = 0
    for rel in sorted(files_a | files_b):
        if rel not in files_a or rel not in files_b:
            print(f"MISSING    {rel}  (only in {'first' if rel in files_a else 'second'} folder)")
            continue
        fa, fb = fingerprint(a / rel), fingerprint(b / rel)
        if fa == fb:
            same += 1
            print(f"SAME       {rel}  {fa}")
        else:
            print(f"DIFFERENT  {rel}  {fa} vs {fb}")
    total = len(files_a | files_b)
    verdict = "IDENTICAL" if same == total else "NOT IDENTICAL"
    print(f"\n{same}/{total} files match: the two runs are {verdict}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python compare_runs.py <folder 1> <folder 2>")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
