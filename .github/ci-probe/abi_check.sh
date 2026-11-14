#!/bin/bash
# CI probe: for every tink wheel in a folder, prints the architectures of the
# tink_bindings extension and whether each slice references the free-threaded
# refcounting entry points (_Py_DecRefShared, _Py_MergeZeroLocalRefcount),
# which only an extension compiled against free-threaded headers uses.
# Informational only: never fails.
set -uo pipefail

readonly WHEEL_DIR="$1"
shopt -s nullglob
for whl in "${WHEEL_DIR}"/tink-*.whl; do
  tmp="$(mktemp -d)"
  unzip -q "${whl}" 'tink/cc/pybind/*' -d "${tmp}"
  for so in "${tmp}"/tink/cc/pybind/tink_bindings*; do
    echo "ABI: $(basename "${whl}"): $(basename "${so}")"
    if [[ "$(uname)" == "Darwin" ]]; then
      archs="$(lipo -archs "${so}")"
      for arch in ${archs}; do
        n="$(nm -u -arch "${arch}" "${so}" \
          | grep -cE '_Py_DecRefShared$|_Py_MergeZeroLocalRefcount$')"
        echo "ABI:   ${arch}: free-threaded refcount symbols referenced: ${n}"
      done
    else
      n="$(nm -D --undefined-only "${so}" \
        | grep -cE '_Py_DecRefShared$|_Py_MergeZeroLocalRefcount$')"
      echo "ABI:   $(uname -m): free-threaded refcount symbols referenced: ${n}"
    fi
  done
  rm -rf "${tmp}"
done
exit 0
