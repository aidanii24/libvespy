import unittest
import hashlib
import shutil
import os

from settings_test import paths
from libvespy import fps4, tlzc


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

    def test_extract_npc_cap_003(self):
        """TLZC Decompression and FPS4 Extraction Test: CAP_I00_03.DAT"""
        # Base Map Decompression
        target: str = os.path.join(paths.CONTROL_DIR, "CAP_I00_03.DAT")
        assert os.path.isfile(target)

        base_dec: str = os.path.join(paths.ARTIFACTS_DIR, "CAP_I00_03.dec")
        tlzc.decompress(target, base_dec)

        base_cs: str = "c9f41b2ebf766373fd617c885ac1941df03c392ccddeff812d0bf2a73ea83f08"
        file_hash: str = ""
        with open(base_dec, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, base_cs, f"Unexpected Output for Decompressed Map!")

        # Base Map Extraction
        ext_dir: str = os.path.join(paths.ARTIFACTS_DIR, "CAP_I00_03.ext")
        ext_mf: str = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "CAP_I00_03.json")

        fps4.extract(base_dec, ext_dir, ext_mf)

        base_ext_fc: int = len(os.listdir(ext_dir))
        self.assertEqual(base_ext_fc, 4, "Unexpected amount of files from Extracted Map!")

        ext_cs: dict[str, str] = {
            "0000": "0cb9f985605aa461b32b01ddb4072cea9d7592cdd8dd4409f300f956cc7182d6",
            "0001": "8f96a8d68481b64827ebe084bfbea788f22c274f6d35d17f1d22c479637bdcc7",
            "0002": "8e87c57f0791c26b7536ed45cafb1e9d61780611fad46b0e9aa69cb0b18899ad",
            "0004": "784585dc00e04ddccfb7c173739cd54bfdcf65a7547464ae4fe1a8b7fc80f4e0",
        }

        for file, cs in ext_cs.items():
            path: str = os.path.join(ext_dir, file)
            self.assertIs(os.path.isfile(path), True, f"Expected {path} to exist!")

            file_hash = ""
            with open(path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            self.assertEqual(file_hash, cs, f"{path} was not extracted correctly!")

        # Chest data decompression
        chest_file: str = os.path.join(ext_dir, "0004")
        chest_dec: str = os.path.join(ext_dir, "0004.dec")

        tlzc.decompress(chest_file, chest_dec)

        self.assertIs(os.path.isfile(chest_dec), True, f"Expected {chest_dec} to exist!")
        chest_dec_cs: str = "065ef89833be99272db2c0eb99bb3eaafcf7507283b60cd35fa30b22ea331888"
        file_hash = ""
        with open(chest_dec, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, chest_dec_cs, f"Chest File (0004) was not decompressed correctly!")

    def test_pack_npc_cap_003(self):
        """TLZC Compression and FPS4 Packing Test: CAP_I00_03.DAT"""
        ext_dir: str = os.path.join(paths.ARTIFACTS_DIR, "CAP_I00_03.ext")
        chest_dec: str = os.path.join(ext_dir, "0004.dec")
        assert os.path.isfile(chest_dec), f"Expected {chest_dec} to exist!"

        tlzc.compress(chest_dec, chest_dec)

        # Checksum based on zlib compression
        chest_com_cs: str = "784585dc00e04ddccfb7c173739cd54bfdcf65a7547464ae4fe1a8b7fc80f4e0"
        file_hash: str = ""
        with open(chest_dec, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, chest_com_cs, f"Chest File (0004) was not compressed correctly!")

        ext_mf: str = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "CAP_I00_03.json")
        assert os.path.isfile(ext_mf), f"Expected {ext_mf} to exist!"

        base_out: str = os.path.join(paths.ARTIFACTS_DIR, "CAP_I00_03.pck")

        fps4.pack_from_manifest(base_out, ext_mf)

        base_cs: str = "c9f41b2ebf766373fd617c885ac1941df03c392ccddeff812d0bf2a73ea83f08"
        file_hash = ""
        with open(base_out, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, base_cs, f"Packed Map file was not packed correctly!")

        cmp_out: str = os.path.join(paths.ARTIFACTS_DIR, "CAP_I00_03.cmp")

        tlzc.compress(base_out, cmp_out)

        cmp_cs: str = "a51520ea94a321a220d3871ed3a3fc612de4435f4d388eca039fad168d1d52d8"
        file_hash = ""
        with open(cmp_out, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, cmp_cs, f"Compressed Map file was not compressed correctly!")

if __name__ == '__main__':
    unittest.main(verbosity=2)