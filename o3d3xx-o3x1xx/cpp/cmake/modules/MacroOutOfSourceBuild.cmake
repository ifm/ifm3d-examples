# [================================================================[
# Macro: MACRO_ENSURE_OUT_OF_SOURCE_BUILD Ensures that the CMake build is
# performed out of the source directory.
#
# Arguments: error_message - A custom error message to display if the build is
# being performed in the source directory or a subdirectory of it.
#
# Behavior: - Compares the source directory (CMAKE_SOURCE_DIR) with the binary
# directory (CMAKE_BINARY_DIR) to check if they are the same (in-source build).
# - Checks if the source directory is a subdirectory of its parent directory. -
# If either condition is true, the macro terminates the configuration process
# with a fatal error and displays the provided error message. Ensures that we do
# an out of source build
# ]==================================================================]
macro(MACRO_ENSURE_OUT_OF_SOURCE_BUILD error_message)
  string(COMPARE EQUAL "${CMAKE_SOURCE_DIR}" "${CMAKE_BINARY_DIR}" insource)
  get_filename_component(PARENTDIR ${CMAKE_SOURCE_DIR} PATH)
  string(COMPARE EQUAL "${CMAKE_SOURCE_DIR}" "${PARENTDIR}" insourcesubdir)
  if(insource OR insourcesubdir)
    message(FATAL_ERROR "${error_message}")
  endif()
endmacro(MACRO_ENSURE_OUT_OF_SOURCE_BUILD)
