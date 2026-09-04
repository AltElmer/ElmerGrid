# Tests

Twelve serial cases and three controls, run by `ctest`. Each case meshes one `.grd` file from `serial/` and checks the result against itself; the controls damage a good mesh in a way one of those checks is supposed to catch, and are marked `WILL_FAIL`.

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

## What each case checks

The Elmer mesh format carries its own redundancy, and that is what is checked: `mesh.header` states how many nodes, bulk elements and boundary elements the mesh has; `mesh.nodes`, `mesh.elements` and `mesh.boundary` then have to list exactly that many; and every node index appearing in the connectivity has to fall inside the node list. Plus the obvious: ElmerGrid exits 0, and it wrote all four files.

That needs no stored reference mesh, which matters here for the reason below.

## The controls

`control.short_node_list_is_caught` truncates `mesh.nodes`, `control.short_element_list_is_caught` truncates `mesh.elements`, and `control.dangling_node_index_is_caught` points the first element at a node one past the end of the node list. All three are marked `WILL_FAIL`, so the suite goes red if any of the checks above ever stops firing.

They exist because the checks report success by saying nothing, which is exactly the shape of check that quietly stops working. Each control was confirmed to fail with the specific message it is meant to provoke, not merely to fail.

## Why the reference meshes in `serial/` are not used

Each `serial/<case>/` directory holds a mesh, and upstream ships two scripts, `serial/checkserialmesh` and `parallel/checkparallelmesh`, that mesh the `.grd` files and `diff` the result against them. Those scripts print the diff and then exit 0 whatever it said, so they have never reported a failure, and nobody has had reason to look.

Measured on 4 September 2026, against `ElmerCSC/elmerfem@devel` built with GCC 15.2 on Windows/UCRT64, eleven of the twelve serial cases do not reproduce:

| cases | what differs |
|---|---|
| `blocks` | nothing; it reproduces exactly |
| `line`, `rect`, `holes`, `tube`, `weight` | float formatting only — the reference writes `0.0` where the current code writes `0`; largest numerical difference is exactly zero |
| `cones`, `cylinder`, `hexframe`, `roll`, `waves` | node coordinates, by 5.3e-08 to 1.07e-04 in absolute terms |
| `barrel` | node ordering and element connectivity, so the meshes are not the same mesh |

Two things are worth saying about that, both checkable.

It is not a recent regression, and it is not caused by [#890](https://github.com/ElmerCSC/elmerfem/pull/890), [#892](https://github.com/ElmerCSC/elmerfem/pull/892) or [#902](https://github.com/ElmerCSC/elmerfem/pull/902). ElmerGrid built at `00610ad`, the commit before the first of those, produces output identical to the current build for all twelve cases — so whatever the reference meshes disagree with, they disagreed with it before that work started.

And the reference meshes cannot have come from the current writer at all. `SaveElmerInput` in `src/egnative.c` builds one format string, `%.<decimals>g`, and applies it to all three coordinates of every node. `%g` prints zero as `0`; there is no value and no precision for which it prints `0.0`. Yet the shipped `line/mesh.nodes` begins `1 -1 0 0.0 0.0` — the same value formatted two different ways on one line. The meshes were written by an older version of that function.

So the reference data is stale rather than wrong, but nothing in the repository records what it was generated from, and the runners cannot tell you either. This suite therefore checks properties that hold for any correct mesh, and cross-platform agreement is checked separately, by `compare_platforms.py` in CI, against the other platforms in the same run rather than against stored data.

This is worth reporting upstream and has nothing to do with modularization; it is noted here so that anyone who runs `checkserialmesh` and sees pages of diff output knows it is not something they broke.

## `compare_platforms.py`

Used by the `determinism` job in CI. It takes a directory of per-platform mesh trees and compares each against a reference platform: `mesh.header`, `mesh.elements` and `mesh.boundary` exactly, after normalising line endings, and `mesh.nodes` to a relative tolerance, since node coordinates go through `libm` and implementations are allowed to differ in the last place.

```
python3 compare_platforms.py --root platforms --reference linux-x86_64-gcc --expect 8 --tolerance 1e-6
```

Exit 0 if every platform agrees, 1 if one disagrees, 3 if it could not tell — fewer than two platforms present, a platform that produced no meshes, or `--expect` not matching what was found. The last of those is deliberate: a platform whose job never uploaded an artifact is invisible to a comparison that only looks at what is there.
