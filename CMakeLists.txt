# ElmerGrid is configured either as part of the Elmer build, where the top
# level project supplies the version information, or on its own directly out
# of this directory.  The block below runs only in the standalone case, so the
# in-tree build is unaffected.
#
# Standalone build:
#   cmake -S elmergrid -B build-elmergrid && cmake --build build-elmergrid
IF(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  CMAKE_MINIMUM_REQUIRED(VERSION 3.12)
  PROJECT(ElmerGrid C)

  IF(NOT CMAKE_BUILD_TYPE)
    SET(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)
  ENDIF()

  # The Elmer top level build sets these, and the sources depend on them:
  # egparallel.c, egnative.c and egextra.c select the one argument form of
  # mkdir() under MINGW32.  Without the definition the build fails to compile
  # on a mingw toolchain.  Mirrors CMakeLists.txt in the Elmer root.
  IF(MINGW)
    ADD_DEFINITIONS(-DMINGW32)
  ENDIF()
  IF(WIN32)
    ADD_DEFINITIONS(-DWIN32)
  ENDIF()

  # config.h.cmake normally picks these up from the Elmer top level build.
  # Only ELMER_FEM_VERSION is set here: fempre.c already handles the case
  # where the branch is unknown, and prints "Rev: NA, Compiled: NA" then.
  IF(NOT DEFINED ELMER_FEM_VERSION)
    SET(ELMER_FEM_VERSION "standalone")
  ENDIF()

  SET(ELMERGRID_STANDALONE TRUE)
  ENABLE_TESTING()
ENDIF()

# FindMetis.cmake normally comes from Elmer's cmake/Modules. A copy lives here
# so this builds without the rest of Elmer. Appended rather than prepended, so
# a parent project that has its own FindMetis keeps using it.
LIST(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/Modules")

# ---------------------------------------------------------------------------
# Metis is a dependency, not part of ElmerGrid.
#
# Upstream carries a copy of METIS 5.1.0, 2013, under src/metis-5.1.0 -- some
# 400 files of somebody else's library inside a tree that also complains about
# exactly that in ElmerCSC/elmerfem#202. This repository does not carry it.
# EXTERNAL_METIS therefore defaults to ON here, where upstream defaults it OFF,
# and that is the one deliberate difference between this tree and upstream's
# elmergrid/ directory.
#
# The bundled copy is one of the two things keeping ElmerGrid off MSVC: GKlib
# compiles with -D__thread=__declspec(thread), which collides with
# corecrt_math.h in the current Windows SDK. Removing it clears that one.
#
# It does not clear the other, and an earlier version of this comment claimed
# it did. egnative.c, egparallel.c and egextra.c include <unistd.h>
# unconditionally, for chdir(), which MSVC spells _chdir in <direct.h>. Four of
# the seven translation units here do compile under cl.exe; those three do not.
#
# Every platform this is built on packages Metis. See the message below.
#
# Default ON in every configuration, including as somebody's subdirectory:
# there is no bundled copy here to fall back to, so OFF has nothing to mean.
# ---------------------------------------------------------------------------
OPTION(EXTERNAL_METIS "Use a Metis installed on the system" ON)

IF(NOT EXTERNAL_METIS)
  MESSAGE(FATAL_ERROR
    "EXTERNAL_METIS=OFF asks for a copy of Metis inside ElmerGrid, and there "
    "is no longer one to build. Install Metis and configure without the "
    "option:\n"
    "  Debian/Ubuntu  apt install libmetis-dev\n"
    "  Fedora/RHEL    dnf install metis-devel\n"
    "  macOS          brew install metis\n"
    "  MSYS2          pacman -S \${MINGW_PACKAGE_PREFIX}-metis\n"
    "  vcpkg          vcpkg install metis\n"
    "  conda          conda install -c conda-forge metis\n"
    "\n"
    "Upstream ElmerCSC/elmerfem still bundles METIS 5.1.0 and builds it by "
    "default; this repository does not carry that copy. See "
    "ElmerCSC/elmerfem#202.")
ENDIF()

CONFIGURE_FILE(config.h.cmake config.h)

ADD_SUBDIRECTORY(src)

# Tests are added only in the standalone build.  Elmer's top level build runs
# its own test suite and must not gain targets from here, which the
# "consumed via add_subdirectory" job in CI checks.
IF(ELMERGRID_STANDALONE)
  ADD_SUBDIRECTORY(tests)
ENDIF()
