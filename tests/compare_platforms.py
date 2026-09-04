#!/usr/bin/env python3
"""Compare the meshes each CI platform produced for the same inputs.

ElmerGrid is deterministic by construction: no threads, no random seeds, no
timing.  The same .grd file should therefore give the same mesh on every
platform and compiler.  Whether it actually does is a measurement, and this is
the instrument.

Connectivity and the header are integers and must match exactly.  Node
coordinates go through libm, whose results are allowed to differ in the last
place between implementations, so those are compared to a relative tolerance.

    python compare_platforms.py --root artifacts --reference linux-x86_64-gcc

Exit codes:
    0  every platform agrees within tolerance
    1  a platform disagrees
    3  could not tell (nothing to compare, or a platform produced no meshes)
"""

from __future__ import annotations

import argparse
import pathlib
import sys

INTEGER_FILES = ("mesh.header", "mesh.elements", "mesh.boundary")
NODE_FILE = "mesh.nodes"


def read_lines(path: pathlib.Path) -> list[str]:
    # Some platforms write CRLF and some LF for the same content, which is a
    # property of the C runtime rather than of the mesh.
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").rstrip("\n").split("\n")


def compare_nodes(ref: pathlib.Path, other: pathlib.Path) -> tuple[float, str | None]:
    """Return (largest relative deviation, first structural complaint)."""
    a, b = read_lines(ref), read_lines(other)
    if len(a) != len(b):
        return (0.0, f"{len(a)} nodes here, {len(b)} there")
    worst = 0.0
    for n, (la, lb) in enumerate(zip(a, b), start=1):
        fa, fb = la.split(), lb.split()
        if len(fa) != len(fb):
            return (worst, f"line {n}: different number of fields")
        if fa[0] != fb[0]:
            return (worst, f"line {n}: node id {fa[0]} vs {fb[0]}")
        for x, y in zip(fa[2:], fb[2:]):
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                return (worst, f"line {n}: {x!r} or {y!r} is not a number")
            d = abs(fx - fy)
            if d:
                scale = max(abs(fx), abs(fy))
                worst = max(worst, d / scale if scale > 1e-12 else d)
    return (worst, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="directory holding one subdirectory per platform")
    ap.add_argument("--reference", required=True, help="the platform every other is compared against")
    ap.add_argument("--tolerance", type=float, default=1e-6,
                    help="largest relative node deviation accepted (default 1e-6)")
    ap.add_argument("--expect", type=int, default=0,
                    help="how many platforms should be present; a platform whose job "
                         "never uploaded anything is invisible here otherwise")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    platforms = sorted(p for p in root.iterdir() if p.is_dir())
    if len(platforms) < 2:
        print(f"::warning::only {len(platforms)} platform(s) under {root}; nothing to compare")
        return 3
    if args.expect and len(platforms) != args.expect:
        print(f"::error::expected {args.expect} platforms, found {len(platforms)}: "
              f"{[p.name for p in platforms]}")
        return 3

    ref_root = root / args.reference
    if not ref_root.is_dir():
        print(f"::error::reference platform {args.reference} is not among {[p.name for p in platforms]}")
        return 3

    cases = sorted(p.name for p in ref_root.iterdir() if p.is_dir())
    if not cases:
        print(f"::error::the reference platform {args.reference} produced no meshes")
        return 3

    print(f"reference: {args.reference}, {len(cases)} cases, tolerance {args.tolerance:g}\n")
    failed = False
    undecided = False

    for platform in platforms:
        if platform.name == args.reference:
            continue
        worst_overall = 0.0
        complaints: list[str] = []
        missing = 0
        for case in cases:
            here, there = ref_root / case, platform / case
            if not there.is_dir():
                missing += 1
                continue
            for name in INTEGER_FILES:
                if not (there / name).exists():
                    complaints.append(f"{case}/{name}: absent")
                elif read_lines(here / name) != read_lines(there / name):
                    complaints.append(f"{case}/{name}: differs")
            if (there / NODE_FILE).exists():
                worst, why = compare_nodes(here / NODE_FILE, there / NODE_FILE)
                worst_overall = max(worst_overall, worst)
                if why:
                    complaints.append(f"{case}/{NODE_FILE}: {why}")
                elif worst > args.tolerance:
                    complaints.append(f"{case}/{NODE_FILE}: relative deviation {worst:.3e}")
            else:
                complaints.append(f"{case}/{NODE_FILE}: absent")

        if missing == len(cases):
            print(f"{platform.name:<28} could not tell -- it produced no meshes")
            undecided = True
        elif complaints:
            print(f"{platform.name:<28} DIFFERS  (worst node deviation {worst_overall:.3e})")
            for c in complaints[:10]:
                print(f"    {c}")
            if len(complaints) > 10:
                print(f"    ... and {len(complaints) - 10} more")
            failed = True
        else:
            print(f"{platform.name:<28} agrees   (worst node deviation {worst_overall:.3e})")

    if failed:
        return 1
    return 3 if undecided else 0


if __name__ == "__main__":
    sys.exit(main())
