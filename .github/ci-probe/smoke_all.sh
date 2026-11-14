#!/bin/bash
# CI probe: runs smoke.py for every tink wheel in a folder, each in a fresh
# venv made from the pyenv Python that matches the wheel's ABI tag (the same
# matching as tools/distribution/test_dist.sh). Prints one RESULT line per
# wheel and fails if any wheel fails.
set -uo pipefail

readonly WHEEL_DIR="$1"
readonly SMOKE_PY="$(cd "$(dirname "$0")" && pwd)/smoke.py"

eval "$(pyenv init -)"

rc=0
shopt -s nullglob
wheels=( "${WHEEL_DIR}"/tink-*.whl )
if (( ${#wheels[@]} == 0 )); then
  echo "RESULT: no wheels in ${WHEEL_DIR}"
  exit 1
fi
for whl in "${wheels[@]}"; do
  name="$(basename "${whl}")"
  abi="$(echo "${name}" | sed -E 's/^tink-[^-]+-cp3[0-9]+-cp3([0-9]+t?)-.*$/3.\1/')"
  minor="${abi%t}"
  flavor=""
  [[ "${abi}" == *t ]] && flavor="t"
  # sed rather than ${minor//./\\.}: macOS runs this with bash 3.2.
  minor_re="$(echo "${minor}" | sed 's/\./\\./g')"
  version="$(pyenv versions --bare \
    | grep -E "^${minor_re}\.[0-9]+${flavor}\$" | tail -1)"
  if [[ -z "${version}" ]]; then
    echo "RESULT: ${name}: FAIL (no pyenv Python for ${abi})"
    rc=1
    continue
  fi
  python="$(pyenv root)/versions/${version}/bin/python3"
  venv="$(mktemp -d)/venv"
  echo "::group::smoke ${name} on ${version}"
  "${python}" -m venv "${venv}"
  if ! "${venv}/bin/python" -m pip install -q "${whl}"; then
    echo "::endgroup::"
    echo "RESULT: ${name} on ${version}: FAIL (pip install)"
    rc=1
    continue
  fi
  "${venv}/bin/python" -I -X faulthandler "${SMOKE_PY}"
  status=$?
  echo "::endgroup::"
  if (( status == 0 )); then
    echo "RESULT: ${name} on ${version} ($(uname -m)): OK"
  else
    if (( status > 128 )); then
      detail="killed by signal $(( status - 128 )) ($(kill -l $(( status - 128 )) 2>/dev/null))"
    else
      detail="exit ${status}"
    fi
    echo "RESULT: ${name} on ${version} ($(uname -m)): FAIL (${detail})"
    rc=1
  fi
done
exit "${rc}"
