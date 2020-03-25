
# IF(CMAKE_CROSSCOMPILING)
#   IF(NATIVE_BUILD_FLAGS)
#     IF(CMAKE_BUILD_TYPE)
#       STRING(TOUPPER _${CMAKE_BUILD_TYPE} _build_type)
#       SET(CMAKE_C_FLAGS${_build_type} "")
#     ELSE()
#       set(CMAKE_BUILD_TYPE Release)
#     ENDIF()
#     SET(CMAKE_C_FLAGS ${NATIVE_BUILD_FLAGS})
#     MESSAGE(STATUS "Resetting build flags for Elmergrid: ${NATIVE_BUILD_FLAGS}")
#   ELSE()
#     MESSAGE(WARNING "Crosscompiling ElmerGrid, no native build flags set")
#   ENDIF()
# ENDIF()

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

cmake_policy(SET CMP0054 NEW)


if (CMAKE_C_COMPILER_ID MATCHES "Clang")
  # using regular Clang or AppleClang
elseif (CMAKE_C_COMPILER_ID STREQUAL "Clang")
  # using Clang
elseif (CMAKE_C_COMPILER_ID STREQUAL "GNU")
  set(CMAKE_C_FLAGS "-Wall -Wextra -Wno-comment")
  set(CMAKE_C_FLAGS_DEBUG "-g")
  set(CMAKE_C_FLAGS_RELEASE "-O3")
elseif (CMAKE_C_COMPILER_ID STREQUAL "Intel")
  # using Intel C++
elseif (CMAKE_C_COMPILER_ID STREQUAL "MSVC")
  set(CMAKE_C_FLAGS "-Wall /wd4668 /wd4710 /wd4774 /wd5045 /wd4102 /wd4820 /wd4701 /wd4100 /wd4703")
  set(CMAKE_C_FLAGS_RELEASE "-O2")  
endif()



IF(MSYS)
  INCLUDE_DIRECTORIES(${/mingw64/include/})
  MESSAGE("You need to have MSYS2's package mingw64/mingw-w64-x86_64-metis installed")
ENDIF()

SET(elmergrid_SRCS common.h femdef.h femelmer.h femfilein.h
  femfileout.h feminfo.h femknot.h femmesh.h 
  femtypes.h nrutil.h common.c femelmer.c femfilein.c femfileout.c
  feminfo.c femknot.c femmesh.c fempre.c 
  nrutil.c)

INCLUDE_DIRECTORIES(${CMAKE_CURRENT_BINARY_DIR})

INCLUDE_DIRECTORIES(${CMAKE_BINARY_DIR}/elmergrid/src)

# ADD_DEFINITIONS(-DDISABLE_MATC)

ADD_EXECUTABLE(ElmerGrid ${elmergrid_SRCS})

TARGET_LINK_LIBRARIES(ElmerGrid metis)

# if(NOT MSVC)
#   target_link_libraries(m)
# endif(NOT MSVC)

IF(NOT(WIN32))
  SET_TARGET_PROPERTIES(ElmerGrid PROPERTIES INSTALL_RPATH "${ELMERSOLVER_RPATH_STRING}")
ENDIF()

INSTALL(TARGETS ElmerGrid RUNTIME DESTINATION "bin")
