#!/bin/sh

# Wrapper script for include path detection with and without cross-compilation

CXX=${CXX:-g++}
COMPILE_COMMANDS=${COMPILE_COMMANDS:-build/compile_commands.json}

# detect and set gcc include paths in a system independent and stable way
CPLUS_INCLUDE_PATH=$($CXX -print-sysroot)/usr/include/c++/$($CXX -dumpversion):$($CXX -print-sysroot)/usr/include/c++/$($CXX -dumpversion)/aarch64-poky-linux
export CPLUS_INCLUDE_PATH

compiled_files() {
    for file in $(echo "$@" | sed -r 's/(-p build )?(.*)/\2/'); do
        # Strip .hpp / .cpp to match all files which have a compiled .cpp file
        file_match=$(
            printf '%s' "$file" | sed -nr \
                "s/(src\/[^\/]*\/)(include\/[^\/]*|src|python\/Bindings|test[s]?)(\/.*)\.[hc]pp/\1.*\3/p"
        )
        if test -z "$file_match"; then
            echo "skipping $file: regex does not match" >&2
            continue
        elif test ! -e "$COMPILE_COMMANDS"; then
            echo "unable to find $COMPILE_COMMANDS" >&2
            exit 1
        elif grep "$file_match" "$COMPILE_COMMANDS" >/dev/null; then
            # echo "using $file: expression $file_match was found in $COMPILE_COMMANDS" >&2
            echo "$file"
        else
            echo "skipping $file: expression $file_match was not found in $COMPILE_COMMANDS" >&2
        fi
    done
}

# Run clang-tidy only on files that are compiled
# shellcheck disable=SC2046
clang-tidy -p build $(compiled_files "$@")
