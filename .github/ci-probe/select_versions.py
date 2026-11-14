"""CI probe: restricts the bdist scripts to the given Python versions.

Usage: python3 select_versions.py 3.14 3.15 3.15t

Only used when the workflow's `versions` input is set; the default run uses
the scripts exactly as they are in the branch. Rewrites the version lists of
tools/distribution/create_bdist.sh (macOS),
tools/distribution/build_linux_binary_wheels.sh (Linux) and
kokoro/gcp_windows/release/bdist/create/run.bat (Windows).
"""

import pathlib
import re
import sys


def _tags(version: str) -> str:
  """Returns '<python tag>-<abi tag>', e.g. 'cp315-cp315t' for '3.15t'."""
  free_threaded = version.endswith('t')
  digits = version.removesuffix('t').replace('.', '')
  return f'cp{digits}-cp{digits}{"t" if free_threaded else ""}'


def _rewrite(path: str, pattern: str, replacement: str) -> None:
  p = pathlib.Path(path)
  # newline='' keeps the CRLF line endings of run.bat.
  with p.open(newline='') as f:
    text = f.read()
  new_text, count = re.subn(pattern, replacement, text, flags=re.M | re.S)
  if count != 1:
    raise SystemExit(f'{path}: expected one match for {pattern!r}, got {count}')
  with p.open('w', newline='') as f:
    f.write(new_text)


def main() -> None:
  versions = sys.argv[1:]
  if not versions:
    raise SystemExit('usage: select_versions.py <version>...')
  for v in versions:
    if not re.fullmatch(r'3\.[0-9]+t?', v):
      raise SystemExit(f'invalid version {v!r}')

  _rewrite(
      'tools/distribution/create_bdist.sh',
      r'^readonly PYTHON_VERSIONS=\([^\r\n]*\)(?=\r?$)',
      'readonly PYTHON_VERSIONS=( ' + ' '.join(f'"{v}"' for v in versions)
      + ' )',
  )

  _rewrite(
      'tools/distribution/build_linux_binary_wheels.sh',
      r'^(PYTHON_VERSIONS\["[^"]+"\]="[^"]+"\r?\n)+',
      ''.join(f'PYTHON_VERSIONS["{v}"]="{_tags(v)}"\n' for v in versions),
  )

  eol = '\r\n'
  block = ''.join(
      f'SET OUT_WHEEL=tink-%TINK_VERSION%-{_tags(v)}-win_amd64.whl{eol}'
      f'CALL :BuildAndInstallWheel "{v}" || GOTO :Error{eol}'
      f'CALL :RunTests "{v}" || GOTO :Error{eol}{eol}'
      for v in versions
  )
  _rewrite(
      'kokoro/gcp_windows/release/bdist/create/run.bat',
      r'^SET OUT_WHEEL=.*?(?=^GOTO :End)',
      block.replace('\\', '\\\\'),
  )


if __name__ == '__main__':
  main()
