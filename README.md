# ElmerGrid

ElmerGrid is the mesh generation, conversion and partitioning utility of the [Elmer](https://github.com/ElmerCSC/elmerfem) finite element package. This repository holds it on its own: it builds, tests and releases without the rest of Elmer, and it carries the history of every commit that ever touched it.

It creates structured 2D meshes of quadrilaterals or triangles, extrudes and revolves them into hexahedra and prisms, reads and writes a long list of mesh formats (Gmsh, the UNIVERSAL file format, COMSOL mphtxt, Ansys, Abaqus, Fidap, VTK and others), applies simple operations such as scaling, rotation, cloning and extrusion, and partitions Elmer meshes either by internal geometric division or with Metis.

## This is an experiment, not a competing distribution

Elmer is developed at [ElmerCSC/elmerfem](https://github.com/ElmerCSC/elmerfem) and that is where ElmerGrid is maintained. This repository exists to answer one question from [ElmerCSC/elmerfem#202](https://github.com/ElmerCSC/elmerfem/issues/202), *cleanup, organization, and modularization*: what does a component of Elmer look like once it stands on its own, and what does it cost to get there?

Nothing here is a proposal to move ElmerGrid out of Elmer. The work that mattered was done upstream, in the open, and merged:

| upstream | what it did |
|---|---|
| [#890](https://github.com/ElmerCSC/elmerfem/pull/890) | ElmerGUI links the ElmerGrid core instead of carrying renamed copies of four of its sources |
| [#892](https://github.com/ElmerCSC/elmerfem/pull/892) | ElmerGrid can be configured as a standalone CMake project, with the in-tree build unchanged |
| [#902](https://github.com/ElmerCSC/elmerfem/pull/902) | ElmerGrid can be built with MATC expression support, which had been unreachable |

Those three merged into `devel` between 1 and 3 September 2026. This repository is what they make possible, and the [`consumed via add_subdirectory`](.github/workflows/ci.yml) job in CI checks the other half of the bargain on every push: a parent project can still add this directory and get exactly what Elmer got before, and nothing else.

Discussion of any of this belongs upstream in [#202](https://github.com/ElmerCSC/elmerfem/issues/202), not in the issue tracker here.

## Building

No dependencies. Metis is bundled and builds with it.

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

The binary lands at `build/src/ElmerGrid`. To build against a Metis installed on the system instead of the bundled copy, add `-DEXTERNAL_METIS=ON`. To build with MATC expression support in `.grd` files, add `-DELMERGRID_WITH_MATC=ON` and supply a `matc` target — [AltElmer/matc](https://github.com/AltElmer/matc) is one.

A parent project that adds this with `add_subdirectory` gets the `ElmerGrid` executable and the `elmergrid_core` library, and no tests. On a MinGW toolchain it must also define `MINGW32` and `WIN32` itself, because `egparallel.c`, `egnative.c` and `egextra.c` select the one-argument form of `mkdir()` from them, and the standalone block that supplies them is skipped when ElmerGrid is not the top level project. Elmer's root `CMakeLists.txt` already defines both, which is why the in-tree build is unaffected; any other parent has to. Measured, not assumed: without them the parent build fails with *too many arguments to function 'mkdir'*, and with them it produces a binary byte-identical in size to the standalone one.

Prebuilt binaries for Linux, macOS and Windows on x86-64 and arm64 are attached to each [release](https://github.com/AltElmer/ElmerGrid/releases). They are self-contained: the release workflow refuses to publish one that depends on anything outside the operating system.

## What CI checks

Ten platform and compiler combinations on every push — GCC, Clang and Intel `icx` on Linux x86-64, GCC on Linux arm64, Clang on macOS arm64 and x86-64, MinGW on Windows x86-64 and arm64, and two of those repeated with `-ffp-contract=off`. Each builds, runs the test suite, and meshes all twelve serial cases.

A further job then compares the meshes. ElmerGrid has no threads, no random seeds and no dependence on timing, so the same `.grd` file should give the same mesh on every one of them. Whether it does is a measurement, and the job is the instrument: connectivity and the header have to match exactly, node coordinates to a mixed absolute and relative tolerance, and a platform that produced nothing is reported as such rather than passing by being absent.

**It already found something.** Eleven of the twelve cases are byte-identical everywhere. `barrel` is not: its connectivity differs on Linux arm64, macOS arm64, Windows arm64 and Intel `icx`, and agrees on every x86-64 GCC, Clang and MinGW build — which is to say, on exactly the targets whose compiler does not contract `a*b + c` into a fused multiply-add by default. The two `-ffp-contract=off` entries in the matrix are there to test that rather than assume it. Details and the numbers are in [tests/README.md](tests/README.md); this is the shape of evidence [ElmerCSC/elmerfem#901](https://github.com/ElmerCSC/elmerfem/issues/901) is missing.

### MSVC

MSVC is not in the matrix, and ElmerGrid is not the reason. Its own sources compile clean under `cl.exe` — all seven `eg*.c` translation units — but the bundled Metis does not: GKlib compiles with `-D__thread=__declspec(thread)`, which collides with `corecrt_math.h` in the current Windows SDK. Sixty-one errors, none of them outside GKlib. A vendored third-party library is the entire obstacle, which is one of the arguments in [#202](https://github.com/ElmerCSC/elmerfem/issues/202).

## Tests

The suite is twelve serial cases plus three controls, and it is described in [tests/README.md](tests/README.md), including why the reference meshes shipped in `tests/serial` are not what it compares against.

## Authors

ElmerGrid was written by **Peter Råback** at CSC – IT Center for Science. Every source file here carries `Author: Peter Raback` and `Copyright (C) 1995- , CSC - IT Center for Science Ltd.`, and 236 of the 352 commits in this repository are his. It has been extended over thirty years by the Elmer developers: Thomas Zwinger, Juhani Kataja, Eelis Takala, Rich Bayless, Markus Mützel, Pavel Ponomarev, Juha Ruokolainen, Sami Ilvonen, Ladislav Michl, Juris Vencels, Mika Malinen and others all appear in `git log`, which is the real record and is complete.

The bundled `src/metis-5.1.0` is [METIS](https://github.com/KarypisLab/METIS), copyright 1995–2013 Regents of the University of Minnesota, under the Apache License 2.0.

## History

Every commit in this repository is an upstream Elmer commit, with its original author, date and message, filtered down to the files that were ever part of ElmerGrid. Nothing was squashed, rewritten or reauthored. The tree at `main` is byte-for-byte the `elmergrid/` directory of `ElmerCSC/elmerfem@devel` — same tree hash — so anything you find here you can find there.

An earlier `master` branch in this repository, from March 2020, was a copy of the sources with no history at all. It is kept as `archive/2020-metisectomy` rather than deleted, since deleting somebody's earlier work is not an improvement, but it should not be used.

## Licence

GPL-2, as upstream, with the linking exception CSC grants in [LICENSES](LICENSES) for METIS and Scotch. See also [GPL-2](GPL-2).
