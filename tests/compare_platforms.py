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


def compare_nodes(ref: pathlib.Path, other: pathlib.Path,
                  rtol: float, atol: float) -> tuple[float, float, bool, str | None]:
    """Return (largest absolute deviation, largest relative deviation, within
    tolerance, first structural complaint).

    A coordinate that is 0 on one platform and 1e-16 on another has a relative
    deviation of 1, which says nothing useful, so the test is the usual mixed
    one: |a - b| <= atol + rtol * |a|.  The relative figure is still reported,
    because it is the informative one away from zero.
    """
    a, b = read_lines(ref), read_lines(other)
    if len(a) != len(b):
        return (0.0, 0.0, False, f"{len(a)} nodes here, {len(b)} there")
    worst_abs = worst_rel = 0.0
    within = True
    for n, (la, lb) in enumerate(zip(a, b), start=1):
        fa, fb = la.split(), lb.split()
        if len(fa) != len(fb):
            return (worst_abs, worst_rel, False, f"line {n}: different number of fields")
        if fa[0] != fb[0]:
            return (worst_abs, worst_rel, False, f"line {n}: node id {fa[0]} vs {fb[0]}")
        for x, y in zip(fa[2:], fb[2:]):
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                return (worst_abs, worst_rel, False, f"line {n}: {x!r} or {y!r} is not a number")
            d = abs(fx - fy)
            if not d:
                continue
            worst_abs = max(worst_abs, d)
            if abs(fx) > 0.0:
                worst_rel = max(worst_rel, d / abs(fx))
            if d > atol + rtol * abs(fx):
                within = False
    return (worst_abs, worst_rel, within, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="directory holding one subdirectory per platform")
    ap.add_argument("--reference", required=True, help="the platform every other is compared against")
    ap.add_argument("--tolerance", type=float, default=1e-9,
                    help="relative node tolerance (default 1e-9)")
    ap.add_argument("--atol", type=float, default=1e-12,
                    help="absolute node tolerance, which is what decides near zero "
                         "(default 1e-12)")
    ap.add_argument("--expect", type=int, default=0,
                    help="how many platforms should be present; a platform whose job "
                         "never uploaded anything is invisible here otherwise")
    ap.add_argument("--known-divergent", action="append", default=[], metavar="CASE",
                    help="a case that is known not to agree everywhere. It is excluded "
                         "from the verdict, and the run fails if it agrees on every "
                         "platform after all, so a stale exemption cannot hide.")
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

    known = set(args.known_divergent)
    unknown_exemptions = known - set(cases)
    if unknown_exemptions:
        print(f"::error::--known-divergent names {sorted(unknown_exemptions)}, "
              f"which are not among the cases {cases}")
        return 3

    print(f"reference: {args.reference}, {len(cases)} cases, "
          f"rtol {args.tolerance:g}, atol {args.atol:g}")
    if known:
        print(f"excluded from the verdict, known not to agree: {sorted(known)}")
    print()

    failed = False
    undecided = False
    diverged_known: set[str] = set()

    for platform in platforms:
        if platform.name == args.reference:
            continue
        worst_abs = worst_rel = 0.0
        complaints: list[str] = []
        excused: list[str] = []
        missing = 0
        for case in cases:
            here, there = ref_root / case, platform / case
            if not there.is_dir():
                missing += 1
                continue
            case_complaints: list[str] = []
            for name in INTEGER_FILES:
                if not (there / name).exists():
                    case_complaints.append(f"{case}/{name}: absent")
                elif read_lines(here / name) != read_lines(there / name):
                    case_complaints.append(f"{case}/{name}: differs")
            if (there / NODE_FILE).exists():
                wa, wr, within, why = compare_nodes(
                    here / NODE_FILE, there / NODE_FILE, args.tolerance, args.atol)
                worst_abs, worst_rel = max(worst_abs, wa), max(worst_rel, wr)
                if why:
                    case_complaints.append(f"{case}/{NODE_FILE}: {why}")
                elif not within:
                    case_complaints.append(
                        f"{case}/{NODE_FILE}: deviates by {wa:.3e} absolute, {wr:.3e} relative")
            else:
                case_complaints.append(f"{case}/{NODE_FILE}: absent")

            if case_complaints and case in known:
                diverged_known.add(case)
                excused.extend(case_complaints)
            else:
                complaints.extend(case_complaints)

        scale = f"worst {worst_abs:.3e} absolute, {worst_rel:.3e} relative"
        if missing == len(cases):
            print(f"{platform.name:<28} could not tell -- it produced no meshes")
            undecided = True
        elif complaints:
            print(f"{platform.name:<28} DIFFERS  ({scale})")
            for c in complaints[:10]:
                print(f"    {c}")
            if len(complaints) > 10:
                print(f"    ... and {len(complaints) - 10} more")
            failed = True
        elif excused:
            print(f"{platform.name:<28} agrees except the known cases  ({scale})")
            for c in excused[:6]:
                print(f"    known: {c}")
        else:
            print(f"{platform.name:<28} agrees   ({scale})")

    # An exemption that is never exercised is an exemption that has outlived
    # whatever it was for, and it would go on hiding a real regression in that
    # case forever.
    stale = known - diverged_known
    if stale:
        print(f"\n::error::{sorted(stale)} agreed on every platform, so the "
              f"--known-divergent exemption is stale and should be removed")
        failed = True

    if failed:
        return 1
    return 3 if undecided else 0


if __name__ == "__main__":
    sys.exit(main())
