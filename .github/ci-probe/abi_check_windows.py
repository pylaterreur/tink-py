"""CI probe: prints the Python DLL that each tink_bindings .pyd imports.

Also says whether it references the free-threaded refcounting entry points
(_Py_DecRefShared, _Py_MergeZeroLocalRefcount), which only an extension
compiled against free-threaded headers uses. Needs pefile (a delvewheel
dependency). Informational only.
"""

import glob
import os
import sys
import zipfile

import pefile

_FT_SYMBOLS = {'_Py_DecRefShared', '_Py_MergeZeroLocalRefcount'}


def main() -> None:
  for whl in sorted(glob.glob(os.path.join(sys.argv[1], 'tink-*.whl'))):
    with zipfile.ZipFile(whl) as z:
      for name in z.namelist():
        if not (name.startswith('tink/cc/pybind/tink_bindings')
                and name.endswith('.pyd')):
          continue
        pe = pefile.PE(data=z.read(name))
        python_dlls = []
        imported = set()
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
          dll = entry.dll.decode()
          if dll.lower().startswith('python'):
            python_dlls.append(dll)
          for imp in entry.imports:
            if imp.name:
              imported.add(imp.name.decode())
        print(f'ABI: {os.path.basename(whl)}: {name}: imports {python_dlls}; '
              'free-threaded refcount symbols referenced: '
              f'{len(imported & _FT_SYMBOLS)}', flush=True)


if __name__ == '__main__':
  main()
