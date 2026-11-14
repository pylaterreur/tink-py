"""CI probe: smoke test of an installed tink wheel.

Imports tink, does an AEAD and an HPKE round trip, prints where the extension
was loaded from, and on free-threaded Python checks that importing tink did
not re-enable the GIL and that the primitives work from several threads.
"""

import sys
import sysconfig
import threading


def main() -> int:
  free_threaded = bool(sysconfig.get_config_var('Py_GIL_DISABLED'))
  print(f'python: {sys.version}', flush=True)
  print(f'executable: {sys.executable}', flush=True)
  print(f'free-threaded build: {free_threaded}', flush=True)

  import tink  # pylint: disable=g-import-not-at-top
  from tink import aead  # pylint: disable=g-import-not-at-top
  from tink import hybrid  # pylint: disable=g-import-not-at-top
  from tink.cc.pybind import tink_bindings  # pylint: disable=g-import-not-at-top

  print(f'tink_bindings: {tink_bindings.__file__}', flush=True)

  aead.register()
  hybrid.register()

  aead_handle = tink.new_keyset_handle(aead.aead_key_templates.AES256_GCM)
  aead_primitive = aead_handle.primitive(aead.Aead)
  ciphertext = aead_primitive.encrypt(b'aead plaintext', b'associated data')
  assert aead_primitive.decrypt(ciphertext, b'associated data') == (
      b'aead plaintext')
  print('AEAD AES256_GCM round trip: OK', flush=True)

  private_handle = tink.new_keyset_handle(
      hybrid.hybrid_key_templates.DHKEM_X25519_HKDF_SHA256_HKDF_SHA256_AES_256_GCM
  )
  hybrid_encrypt = private_handle.public_keyset_handle().primitive(
      hybrid.HybridEncrypt)
  hybrid_decrypt = private_handle.primitive(hybrid.HybridDecrypt)
  ciphertext = hybrid_encrypt.encrypt(b'hpke plaintext', b'context info')
  assert hybrid_decrypt.decrypt(ciphertext, b'context info') == (
      b'hpke plaintext')
  print('HPKE X25519/HKDF-SHA256/AES-256-GCM round trip: OK', flush=True)

  gil_enabled = (
      sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else True)  # pylint: disable=protected-access
  print(f'GIL enabled after import tink: {gil_enabled}', flush=True)

  if free_threaded:
    if gil_enabled:
      print('FAIL: import tink re-enabled the GIL', flush=True)
      return 1
    errors = []

    def work() -> None:
      try:
        for i in range(200):
          data = bytes([i % 256]) * 64
          c = aead_primitive.encrypt(data, b'ad')
          assert aead_primitive.decrypt(c, b'ad') == data
          c = hybrid_encrypt.encrypt(data, b'ctx')
          assert hybrid_decrypt.decrypt(c, b'ctx') == data
      except Exception as e:  # pylint: disable=broad-exception-caught
        errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(16)]
    for t in threads:
      t.start()
    for t in threads:
      t.join()
    if errors:
      print(f'FAIL: errors in threads: {errors!r}', flush=True)
      return 1
    print('16 threads x 200 AEAD + HPKE round trips: OK', flush=True)

  print('SMOKE OK', flush=True)
  return 0


if __name__ == '__main__':
  sys.exit(main())
