import unittest
import hashlib
import shutil
import os

from settings_test import paths
from libvespy import tlzc


class TestTLZC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create clean artifacts folder"""
        contents: list[str] = os.listdir(paths.ARTIFACTS_DIR)
        for content in contents:
            path: str = os.path.join(paths.ARTIFACTS_DIR, content)
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)

    def setUp(self):
        """Display current Test Case"""
        print(self._testMethodDoc)

    def test_decompress_tlzc(self):
        """TLZC Decompression Test: AHO_I00_02.DAT"""
        target = os.path.join(paths.CONTROL_DIR, "AHO_I00_02.DAT")
        assert os.path.isfile(target)

        output = os.path.join(paths.ARTIFACTS_DIR, "dec_AHO_I00_02.DAT")

        tlzc.decompress(target, output)

        assert os.path.isfile(output)

        checksum: str = "c260bd42d5a74f822edaedcc43fafbb08562e85174fcd069b72632b6c4953303"
        file_hash: str = ""
        with open(output, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum)

    def test_compress_tlzc_zlib(self):
        """TLZC zlib Compression Test: AHO_I00_02.DAT"""
        target = os.path.join(paths.CONTROL_DIR, "AHO_I00_02.tlzc")
        assert os.path.isfile(target), f"{target} was not found"

        output = os.path.join(paths.ARTIFACTS_DIR, "com_AHO_I00_02.DAT")

        tlzc.compress(target, output, 2)

        assert os.path.isfile(output)

        # Compressed by Hyouta with zlib (Type 2)
        checksum: str = "93c61d8f853e827116c4cc0bd3da56e10fd64fccc2e56841af68b89d96554f39"
        file_hash: str = ""
        with open(output, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum)

if __name__ == '__main__':
    unittest.main()