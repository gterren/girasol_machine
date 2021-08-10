#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "uvc" for configuration "Release"
set_property(TARGET uvc APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(uvc PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "/usr/lib/x86_64-linux-gnu/libusb-1.0.so"
  IMPORTED_LOCATION_RELEASE "/usr/local/lib/libuvc.so"
  IMPORTED_SONAME_RELEASE "libuvc.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS uvc )
list(APPEND _IMPORT_CHECK_FILES_FOR_uvc "/usr/local/lib/libuvc.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
