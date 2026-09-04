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

CONFIGURE_FILE(config.h.cmake config.h)

ADD_SUBDIRECTORY(src)

# Tests are added only in the standalone build.  Elmer's top level build runs
# its own test suite and must not gain targets from here, which the
# "consumed via add_subdirectory" job in CI checks.
IF(ELMERGRID_STANDALONE)
  ADD_SUBDIRECTORY(tests)
ENDIF()
