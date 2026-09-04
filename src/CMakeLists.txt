
IF(CMAKE_CROSSCOMPILING)
  IF(NATIVE_BUILD_FLAGS)
    IF(CMAKE_BUILD_TYPE)
      STRING(TOUPPER _${CMAKE_BUILD_TYPE} _build_type)
      SET(CMAKE_C_FLAGS${_build_type} "")
    ENDIF()
    SET(CMAKE_C_FLAGS ${NATIVE_BUILD_FLAGS})
    MESSAGE(STATUS "Resetting build flags for Elmergrid: ${NATIVE_BUILD_FLAGS}")
  ELSE()
    MESSAGE(WARNING "Crosscompiling ElmerGrid, no native build flags set")
  ENDIF()
ENDIF()

SET(elmergrid_SRCS egdef.h egparallel.h egnative.h egconvert.h
  egexport.h egextra.h egmesh.h 
  egtypes.h egutils.h egparallel.c egnative.c egconvert.c egexport.c
  egextra.c egmesh.c fempre.c 
  egutils.c)

ADD_EXECUTABLE(ElmerGrid ${elmergrid_SRCS})

# Metis comes from the system. The bundled METIS 5.1.0 that upstream builds
# when EXTERNAL_METIS is OFF is not in this repository; the top level
# CMakeLists.txt refuses that configuration with the package names to install.
FIND_PACKAGE(Metis)
IF(NOT Metis_FOUND)
  MESSAGE(FATAL_ERROR
    "  Metis library not found. Install it, or point the build at one with "
    "-DMETISROOT=<prefix>. The top level CMakeLists.txt lists the package "
    "name for each platform.")
ENDIF()

# The include directory is added here rather than left to the imported target.
#
# FindMetis.cmake creates an imported `metis` target carrying
# INTERFACE_INCLUDE_DIRECTORIES, but only along one of its two paths: when
# Metis_LIBRARIES and Metis_INCLUDE_DIR are already set -- which is how a
# caller pins a particular Metis, and how the release workflow selects the
# static one -- it sets Metis_FOUND and RETURNs before creating anything. The
# link then succeeds by name while metis.h is not on the include path, so the
# failure is a missing header rather than a missing library, and only on
# platforms where the prefix is not already searched. It passed on MSYS2 and
# Linux for that reason and failed on macOS arm64.
#
# Same shape as ElmerCSC/elmerfem#907 in FindARPACK: a find module that reports
# success without producing the target its callers rely on.
TARGET_INCLUDE_DIRECTORIES(ElmerGrid SYSTEM PRIVATE ${Metis_INCLUDE_DIR})

# config.h is generated into the elmergrid binary directory and reached as
# "../config.h" from the sources here, so this directory is what is needed.
TARGET_INCLUDE_DIRECTORIES(ElmerGrid PRIVATE
  ${CMAKE_CURRENT_BINARY_DIR})

# ---------------------------------------------------------------------------
# MATC in ElmerGrid
#
# ElmerGrid can evaluate MATC expressions in .grd files: egnative.c calls
# mtc_domath() and mtc_init() under "#if USE_MATC", and egdef.h derives
# USE_MATC from DISABLE_MATC.  Defining DISABLE_MATC unconditionally, as this
# file used to, made that unreachable and left no way to ask for it.
#
# The option is OFF by default, so nothing changes unless it is asked for.
# Enabling it needs the matc library, which the Elmer build provides:
# ADD_SUBDIRECTORY(matc) in the top level CMakeLists.txt is unconditional and
# runs before this directory.  The TARGET check keeps a standalone ElmerGrid
# build working, where no such target exists and MATC simply stays off.
#
# No header is needed: egnative.c declares both functions itself.
#
# See ElmerCSC/elmerfem#899 for what enabling this is ultimately for.
# ---------------------------------------------------------------------------
OPTION(ELMERGRID_WITH_MATC "Build ElmerGrid with MATC expression support" OFF)

IF(ELMERGRID_WITH_MATC AND NOT TARGET matc)
  MESSAGE(WARNING
    "  [ElmerGrid] ELMERGRID_WITH_MATC is ON but no 'matc' target exists; "
    "building without MATC.")
ENDIF()

IF(ELMERGRID_WITH_MATC AND TARGET matc)
  MESSAGE(STATUS "  [ElmerGrid] MATC:                     ON")
  TARGET_LINK_LIBRARIES(ElmerGrid PRIVATE matc)
ELSE()
  TARGET_COMPILE_DEFINITIONS(ElmerGrid PRIVATE DISABLE_MATC)
ENDIF()

TARGET_LINK_LIBRARIES(ElmerGrid PRIVATE metis m)
IF(NOT(WIN32))
  SET_TARGET_PROPERTIES(ElmerGrid PROPERTIES INSTALL_RPATH "${ELMERSOLVER_RPATH_STRING}")
ENDIF()

INSTALL(TARGETS ElmerGrid RUNTIME DESTINATION "bin")

# ---------------------------------------------------------------------------
# ElmerGrid core library, used by the ElmerGrid plugin inside ElmerGUI.
#
# ElmerGUI embeds the ElmerGrid mesh handling routines.  Until now it carried
# its own copies of egconvert.c, egmesh.c, egnative.c and egutils.c under
# ElmerGUI/Application/plugins, renamed to .cpp and refreshed by hand with
# plugins/grid2gui.sh.  Those copies are gone and ElmerGUI links this library
# instead, so there is a single copy of these sources in the tree.
#
# EG_PLUGIN selects the embedded configuration (USE_MATC 0, USE_METIS 0), which
# is what ElmerGUI has always defined for its copies.  It is PUBLIC so that the
# setting reaching this library and the setting reaching ElmerGUI's own sources
# cannot drift apart.
#
# The headers declaring these routines carry extern "C" guards, so C++ callers
# such as ElmerGUI can include them directly.
# ---------------------------------------------------------------------------
SET(elmergrid_core_SRCS
  egconvert.c egmesh.c egnative.c egutils.c
  egconvert.h egmesh.h egnative.h egutils.h
  egdef.h egtypes.h)

ADD_LIBRARY(elmergrid_core STATIC ${elmergrid_core_SRCS})

TARGET_COMPILE_DEFINITIONS(elmergrid_core PUBLIC EG_PLUGIN)

TARGET_INCLUDE_DIRECTORIES(elmergrid_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

SET_TARGET_PROPERTIES(elmergrid_core PROPERTIES POSITION_INDEPENDENT_CODE TRUE)

IF(NOT(WIN32))
  TARGET_LINK_LIBRARIES(elmergrid_core PUBLIC m)
ENDIF()
