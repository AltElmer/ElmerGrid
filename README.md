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

## The bundled METIS is gone

Upstream carries a copy of METIS 5.1.0 from 2013 under `elmergrid/src/metis-5.1.0` — 137 files of somebody else's library, inside the tree whose [#202](https://github.com/ElmerCSC/elmerfem/issues/202) complains about exactly that practice. This repository does not carry it. `EXTERNAL_METIS` defaults to `ON` here where upstream defaults it `OFF`, and configuring with `-DEXTERNAL_METIS=OFF` fails with the package name for each platform rather than silently building a vendored copy.

Every platform in the CI matrix packages Metis: `libmetis-dev`, `brew install metis`, `pacman -S ${MINGW_PACKAGE_PREFIX}-metis`, `vcpkg install metis`. What it costs and what it buys, measured on MSYS2 UCRT64:

| | bundled | system Metis |
|---|---|---|
| tracked files | 303 | **166** |
| `ctest` | 15/15 | **15/15** |
| `ElmerGrid 1 2 angle_metis.grd -metis 5` | 5 partitions | **5 partitions** |
| `ElmerGrid.exe`, shared Metis | — | 747,058 bytes |
| `ElmerGrid.exe`, static Metis (what a release ships) | 1,038,685 bytes | 1,198,000 bytes |

What shrinks is the repository, not the binary — a statically linked release still carries Metis, and this one carries slightly more of it than the 2013 copy did. The saving is 137 files of vendored third-party source that nobody here was maintaining.

The `-metis 5` row is the one that matters. Partitioning is what Metis is *for*, so a build that links and passes the mesh tests proves nothing about it; it was run, on both the shared and the static build.

One trap worth recording, because the release gate is what caught it: `-static` alone is not enough. `pkg-config` hands `FindMetis.cmake` the full path to `libmetis.dll.a`, and a full path beats the linker's preference for archives, so the "static" binary came out importing `libmetis.dll`. The release workflow names `libmetis.a` explicitly and fails if it cannot find one.

This is the one deliberate difference between this tree and upstream's `elmergrid/`, and it is the point of the exercise rather than an accident of extraction.

## Building

Metis is the only dependency.

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

The binary lands at `build/src/ElmerGrid`. To build against a Metis installed on the system instead of the bundled copy, add `-DEXTERNAL_METIS=ON`. To build with MATC expression support in `.grd` files, add `-DELMERGRID_WITH_MATC=ON` and supply a `matc` target — [AltElmer/matc](https://github.com/AltElmer/matc) is one.

A parent project that adds this with `add_subdirectory` gets the `ElmerGrid` executable and the `elmergrid_core` library, and no tests. On a MinGW toolchain it must also define `MINGW32` and `WIN32` itself, because `egparallel.c`, `egnative.c` and `egextra.c` select the one-argument form of `mkdir()` from them, and the standalone block that supplies them is skipped when ElmerGrid is not the top level project. Elmer's root `CMakeLists.txt` already defines both, which is why the in-tree build is unaffected; any other parent has to. Measured, not assumed: without them the parent build fails with *too many arguments to function 'mkdir'*, and with them it produces a binary byte-identical in size to the standalone one.

Prebuilt binaries for Linux, macOS and Windows on x86-64 and arm64 are attached to each [release](https://github.com/AltElmer/ElmerGrid/releases). They are self-contained: the release workflow refuses to publish one that depends on anything outside the operating system.

## What CI checks

Eleven platform and compiler combinations on every push — GCC, Clang and Intel `icx` on Linux x86-64, GCC on Linux arm64, Clang on macOS arm64 and x86-64, MinGW on Windows x86-64 and arm64, and three of those repeated under different floating-point settings. Each builds, runs the test suite, and meshes all twelve serial cases.

A further job then compares the meshes. ElmerGrid has no threads, no random seeds and no dependence on timing, so the same `.grd` file should give the same mesh on every one of them. Whether it does is a measurement, and the job is the instrument: connectivity and the header have to match exactly, node coordinates to a mixed absolute and relative tolerance, and a platform that produced nothing is reported as such rather than passing by being absent.

**It already found something.** Eleven of the twelve cases are byte-identical everywhere. `barrel` is not: its connectivity differs on Linux arm64, macOS arm64, Windows arm64 and Intel `icx`, and agrees on every x86-64 GCC, Clang and MinGW build. Rebuilding arm64 with `-ffp-contract=off` makes it agree exactly; `icx` needs the wider `-fp-model=precise`, since `-ffp-contract=off` alone does not fix it.

Which gives the result worth stating: **under strict IEEE floating-point semantics ElmerGrid is bit-reproducible across four operating systems, two architectures and four compilers.** Under each compiler's defaults it is not, and it fails in the awkward way — `icx` matches the reference to 1.776e-14 and still produces a *different mesh*, because node merging decides a topological question on a last-place difference. Nothing warns. Numbers and method in [tests/README.md](tests/README.md); this is the shape of evidence [ElmerCSC/elmerfem#901](https://github.com/ElmerCSC/elmerfem/issues/901) is missing.

### MSVC

MSVC is not in the matrix, and there are exactly two reasons. Both were measured, and the second one corrects an earlier claim here that the first was the whole story.

The bundled METIS was one of them: GKlib compiles with `-D__thread=__declspec(thread)`, which collides with `corecrt_math.h` in the current Windows SDK. That was 61 errors, and removing the bundled copy removed all of them.

What is left is ElmerGrid's own. `egnative.c`, `egparallel.c` and `egextra.c` include `<unistd.h>` unconditionally, for `chdir()`, which MSVC spells `_chdir` in `<direct.h>`. So four of the seven translation units compile under `cl.exe` and three do not. Guarding that include is a change to upstream source files and belongs in a pull request there, not quietly here.

## Tests

The suite is twelve serial cases plus three controls, and it is described in [tests/README.md](tests/README.md), including why the reference meshes shipped in `tests/serial` are not what it compares against.

## Authors

ElmerGrid was written by **Peter Råback** at CSC – IT Center for Science. Every source file here carries `Author: Peter Raback` and `Copyright (C) 1995- , CSC - IT Center for Science Ltd.`, and 236 of the 352 commits in this repository are his. It has been extended over thirty years by the Elmer developers: Thomas Zwinger, Juhani Kataja, Eelis Takala, Rich Bayless, Markus Mützel, Pavel Ponomarev, Juha Ruokolainen, Sami Ilvonen, Ladislav Michl, Juris Vencels, Mika Malinen and others all appear in `git log`, which is the real record and is complete.

The bundled `src/metis-5.1.0` is [METIS](https://github.com/KarypisLab/METIS), copyright 1995–2013 Regents of the University of Minnesota, under the Apache License 2.0.

## History

Every commit in this repository is an upstream Elmer commit, with its original author, date and message, filtered down to the files that were ever part of ElmerGrid. Nothing was squashed, rewritten or reauthored. The extraction was verified by tree hash: at the point it was taken, `0407aaf1417a2e0ff074ab758044a44e4bb47608` was both this tree and `ElmerCSC/elmerfem@devel:elmergrid`. Everything after that commit is this repository's own — the tests, the CI, and the removal of the bundled METIS.

An earlier `master` branch in this repository, from March 2020, was a copy of the sources with no history at all. It is kept as `archive/2020-metisectomy` rather than deleted, since deleting somebody's earlier work is not an improvement, but it should not be used.

## Licence

GPL-2, as upstream, with the linking exception CSC grants in [LICENSES](LICENSES) for METIS and Scotch. See also [GPL-2](GPL-2).
