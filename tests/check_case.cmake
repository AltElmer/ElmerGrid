# Run one ElmerGrid case and check the mesh it wrote against itself.
#
# The mesh files carry their own redundancy: mesh.header states how many nodes,
# bulk elements and boundary elements the mesh has, and the other three files
# then list exactly that many.  Element connectivity indexes into the node
# list, so every index has to fall inside it.  Checking those identities needs
# no stored reference mesh, which matters here -- see tests/README.md for why
# the reference meshes shipped under tests/serial cannot be used for this.
#
# Invoked as:
#   cmake -DEG=<ElmerGrid> -DGRD=<file.grd> -DWORK=<dir> -DCASE=<name>
#         [-DCORRUPT=<file>] [-DBADINDEX=1] -P check_case.cmake
#
# CORRUPT and BADINDEX are for the controls.  Each damages the mesh after
# ElmerGrid has written it, in a way one of the checks below is supposed to
# catch, and the test that uses it is marked WILL_FAIL.  Without them the
# checks would report success by saying nothing, which is indistinguishable
# from a check that has quietly stopped working.

foreach(v EG GRD WORK CASE)
  if(NOT DEFINED ${v})
    message(FATAL_ERROR "check_case.cmake: -D${v} is required")
  endif()
endforeach()

get_filename_component(_grd_dir "${GRD}" DIRECTORY)
get_filename_component(_grd_name "${GRD}" NAME)
set(_out "${WORK}/${CASE}")

file(REMOVE_RECURSE "${_out}")
file(MAKE_DIRECTORY "${WORK}")

# ElmerGrid resolves relative paths against the working directory, so it is run
# from the directory holding the .grd file.
execute_process(
  COMMAND "${EG}" 1 2 "${_grd_name}" -out "${_out}"
  WORKING_DIRECTORY "${_grd_dir}"
  RESULT_VARIABLE _rc
  OUTPUT_VARIABLE _stdout
  ERROR_VARIABLE _stderr)

if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "${CASE}: ElmerGrid exited ${_rc}\n${_stdout}\n${_stderr}")
endif()

foreach(f mesh.header mesh.nodes mesh.elements mesh.boundary)
  if(NOT EXISTS "${_out}/${f}")
    message(FATAL_ERROR "${CASE}: ElmerGrid exited 0 but wrote no ${f}")
  endif()
endforeach()

if(DEFINED CORRUPT)
  # Deliberately damage the mesh so the checks below have something to catch.
  file(READ "${_out}/${CORRUPT}" _text)
  string(LENGTH "${_text}" _len)
  math(EXPR _half "${_len} / 2")
  string(SUBSTRING "${_text}" 0 ${_half} _text)
  file(WRITE "${_out}/${CORRUPT}" "${_text}")
  message(STATUS "${CASE}: control -- truncated ${CORRUPT} to ${_half} bytes")
endif()

if(BADINDEX)
  # Point the last node of the first bulk element one past the end of the node
  # list, which is the shape of corruption the connectivity check looks for.
  file(STRINGS "${_out}/mesh.header" _h)
  list(GET _h 0 _c)
  string(REGEX MATCHALL "[0-9]+" _c "${_c}")
  list(GET _c 0 _n)
  math(EXPR _n "${_n} + 1")
  file(STRINGS "${_out}/mesh.elements" _els)
  list(GET _els 0 _first_el)
  string(REGEX REPLACE "[0-9]+([ \t\r]*)$" "${_n}\\1" _patched "${_first_el}")
  list(REMOVE_AT _els 0)
  list(INSERT _els 0 "${_patched}")
  string(REPLACE ";" "\n" _els "${_els}")
  file(WRITE "${_out}/mesh.elements" "${_els}\n")
  message(STATUS "${CASE}: control -- first element now references node ${_n}")
endif()

# file(STRINGS) drops the line terminator, so CRLF and LF both read the same.
file(STRINGS "${_out}/mesh.header" _header)
list(GET _header 0 _counts)
string(REGEX MATCHALL "[0-9]+" _counts "${_counts}")
list(LENGTH _counts _n)
if(_n LESS 3)
  message(FATAL_ERROR "${CASE}: mesh.header first line is not three counts: ${_counts}")
endif()
list(GET _counts 0 _nnodes)
list(GET _counts 1 _nelements)
list(GET _counts 2 _nboundary)

function(_count_lines path out)
  file(STRINGS "${path}" _lines)
  list(LENGTH _lines _n)
  set(${out} ${_n} PARENT_SCOPE)
endfunction()

_count_lines("${_out}/mesh.nodes" _got_nodes)
_count_lines("${_out}/mesh.elements" _got_elements)
_count_lines("${_out}/mesh.boundary" _got_boundary)

set(_errors "")
if(NOT _got_nodes EQUAL _nnodes)
  list(APPEND _errors "mesh.header says ${_nnodes} nodes, mesh.nodes has ${_got_nodes} lines")
endif()
if(NOT _got_elements EQUAL _nelements)
  list(APPEND _errors "mesh.header says ${_nelements} elements, mesh.elements has ${_got_elements} lines")
endif()
if(NOT _got_boundary EQUAL _nboundary)
  list(APPEND _errors "mesh.header says ${_nboundary} boundary elements, mesh.boundary has ${_got_boundary} lines")
endif()

# Every node index named by a bulk element must exist.  Fields are
#   <id> <body> <type> <node> <node> ...
# so the connectivity starts at the fourth field.
file(STRINGS "${_out}/mesh.elements" _elements)
set(_bad_index "")
foreach(_line IN LISTS _elements)
  string(REGEX MATCHALL "[0-9]+" _f "${_line}")
  list(LENGTH _f _nf)
  if(_nf GREATER 3)
    math(EXPR _last "${_nf} - 1")
    foreach(_i RANGE 3 ${_last})
      list(GET _f ${_i} _idx)
      if(_idx LESS 1 OR _idx GREATER _nnodes)
        set(_bad_index "${_line}")
        break()
      endif()
    endforeach()
  endif()
  if(NOT _bad_index STREQUAL "")
    break()
  endif()
endforeach()
if(NOT _bad_index STREQUAL "")
  list(APPEND _errors "an element indexes a node outside 1..${_nnodes}: ${_bad_index}")
endif()

if(_errors)
  string(REPLACE ";" "\n  " _errors "${_errors}")
  message(FATAL_ERROR "${CASE}: the mesh is not self-consistent\n  ${_errors}")
endif()

message(STATUS
  "${CASE}: ${_nnodes} nodes, ${_nelements} elements, ${_nboundary} boundary elements -- consistent")
