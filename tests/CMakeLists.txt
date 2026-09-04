# Tests for the standalone ElmerGrid build.  Added only when ElmerGrid is the
# top level project; Elmer's own build runs its own suite and never reaches
# this directory.

set(_check "${CMAKE_CURRENT_SOURCE_DIR}/check_case.cmake")
set(_work "${CMAKE_CURRENT_BINARY_DIR}/work")

file(GLOB _grds RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/serial"
     "${CMAKE_CURRENT_SOURCE_DIR}/serial/*.grd")
list(SORT _grds)

if(NOT _grds)
  message(FATAL_ERROR "no .grd files under tests/serial -- the suite would be empty")
endif()

foreach(_grd IN LISTS _grds)
  get_filename_component(_case "${_grd}" NAME_WE)
  add_test(NAME serial.${_case}
    COMMAND "${CMAKE_COMMAND}"
            -DEG=$<TARGET_FILE:ElmerGrid>
            -DGRD=${CMAKE_CURRENT_SOURCE_DIR}/serial/${_grd}
            -DWORK=${_work}
            -DCASE=${_case}
            -P "${_check}")
endforeach()

list(LENGTH _grds _n)
message(STATUS "  [ElmerGrid] tests:                    ${_n} serial cases")

# ---------------------------------------------------------------------------
# The controls.
#
# Every check above reports success by saying nothing, which is the shape of
# check that quietly stops working.  Each control damages a good mesh in a way
# one of the checks is supposed to catch and is marked WILL_FAIL, so the suite
# goes red if that check ever stops firing.  They are the reason to believe the
# twelve tests above mean anything.
#
# The upstream runners this replaces, tests/serial/checkserialmesh and
# tests/parallel/checkparallelmesh, print diff output and always exit 0, so
# they report success whatever ElmerGrid produces.
# ---------------------------------------------------------------------------
list(GET _grds 0 _first)
get_filename_component(_first_case "${_first}" NAME_WE)

function(_add_control name)
  add_test(NAME control.${name}
    COMMAND "${CMAKE_COMMAND}"
            -DEG=$<TARGET_FILE:ElmerGrid>
            -DGRD=${CMAKE_CURRENT_SOURCE_DIR}/serial/${_first}
            -DWORK=${_work}/control_${name}
            -DCASE=control_${name}
            ${ARGN}
            -P "${_check}")
  set_tests_properties(control.${name} PROPERTIES WILL_FAIL TRUE)
endfunction()

_add_control(short_node_list_is_caught      -DCORRUPT=mesh.nodes)
_add_control(short_element_list_is_caught   -DCORRUPT=mesh.elements)
_add_control(dangling_node_index_is_caught  -DBADINDEX=1)
