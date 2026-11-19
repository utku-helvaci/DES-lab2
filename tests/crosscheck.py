#!/usr/bin/env python3
"""
crosscheck.py - compares our DES (bin/des_trace -q) with two independent
implementations on random keys and blocks, in both directions:

  * pycryptodome  (pip install pycryptodome)
  * the OpenSSL command line (DES needs OpenSSL 3's "legacy" provider)

A missing reference implementation is reported and skipped.
Usage:  python3 tests/crosscheck.py [count]
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DES_TRACE = os.path.join(HERE, "..", "bin", "des_trace")


def ours(key: bytes, block: bytes, decrypt: bool = False) -> str:
    args = [DES_TRACE, "-q", "-k", key.hex(), "-i", block.hex()]
    if decrypt:
        args.append("-d")
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def openssl(key: bytes, block: bytes, decrypt: bool = False):
    args = ["openssl", "enc", "-des-ecb", "-nopad", "-K", key.hex(),
            "-provider", "legacy", "-provider", "default"]
    if decrypt:
        args.append("-d")
    result = subprocess.run(args, input=block, capture_output=True)
    return result.stdout.hex() if result.returncode == 0 else None


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    try:
        from Crypto.Cipher import DES  # pycryptodome
    except ImportError:
        DES = None
        print("pycryptodome not installed - skipped")
    have_openssl = shutil.which("openssl") is not None and \
        openssl(bytes(8), bytes(8)) is not None
    if not have_openssl:
        print("openssl with the legacy provider not available - skipped")
    if DES is None and not have_openssl:
        return 1

    failures = compared = 0
    for i in range(count):
        key, block = os.urandom(8), os.urandom(8)
        enc, dec = ours(key, block), ours(key, block, decrypt=True)
        refs = []
        if DES is not None:
            cipher = DES.new(key, DES.MODE_ECB)
            refs.append(("pycryptodome", cipher.encrypt(block).hex(), cipher.decrypt(block).hex()))
        if have_openssl and i < 50:  # the CLI is slow: first 50 pairs only
            refs.append(("openssl", openssl(key, block), openssl(key, block, decrypt=True)))
        for name, ref_enc, ref_dec in refs:
            compared += 2
            if enc != ref_enc or dec != ref_dec:
                failures += 1
                print(f"MISMATCH ({name}) key={key.hex()} block={block.hex()}: "
                      f"ours {enc}/{dec}, {name} {ref_enc}/{ref_dec}")

    print(f"cross-check: {count} random key/block pairs, {compared} comparisons "
          f"(encrypt + decrypt) against pycryptodome"
          f"{' and openssl' if have_openssl else ''}: {failures} mismatches")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
