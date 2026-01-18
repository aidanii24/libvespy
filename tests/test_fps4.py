import unittest
import hashlib
import shutil
import os

from settings_test import paths
from libvespy import fps4


class TestFPS4(unittest.TestCase):
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

    @unittest.skip("skipping this test")
    def test_extract_btl(self):
        """FPS4 Extraction Test: btl.svo"""
        target = os.path.join(paths.CONTROL_DIR, 'btl.svo')
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, 'ext_btl')
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, '.manifest', 'btl.json')

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 3, msg='Expected 3 output files')

        control_checksums: dict[str, str] = {
            "BTL_EFFECT.DAT": "5d75b49a0129e3e6eb2dc17fdf1923d70d29f592cc5790387c93889036eb3af5",
            "BTL_EFFECT.DAV": "c20827f1e76c7a1ba55b3e320171ecbca45da94fa022d73aab2d1cf3793e3452",
            "BTL_PACK.DAT": "2587565b2581041d063f8eaf8346bf13cbc52c60b3e194f6e6eb41ea6771350f"
        }

        for file in os.listdir(out_dir):
            file_path: str = os.path.join(out_dir, file)
            self.assertIs(os.path.isfile(file_path), True, msg=f"{file} should exist")

            file_hash: str = ""
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                f.close()

            self.assertEqual(file_hash, control_checksums[file], msg=f"{file} does not match checksum")

    @unittest.skip("skipping this test")
    def test_extract_btl_pack(self):
        """FPS4 Extraction Test: BTL_PACK.DAT"""
        target = os.path.join(paths.CONTROL_DIR, "BTL_PACK.DAT")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_BTL_PACK")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "BTL_PACK.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 24, msg='Expected 24 output files')

    @unittest.skip("skipping this test")
    def test_extract_T8BTMA(self):
        """FPS4 Extraction Test: 0004"""
        target = os.path.join(paths.CONTROL_DIR, "0004")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_T8BTMA")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "T8BTMA.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 1, msg='Expected 1 output file')

        checksum: str = "cabe525276242a5d5421f5cb52b2f64ea39a0549719da7779fb577783da19016"
        file_hash: str = ""
        with open(os.path.join(out_dir, os.listdir(out_dir)[0]), "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum, msg=f"{out_dir} does not match checksum")

    @unittest.skip("skipping this test")
    def test_extract_item(self):
        """FPS4 Extraction Test: item.svo"""
        target = os.path.join(paths.CONTROL_DIR, "item.svo")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_item")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "item.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 2, msg='Expected 2 output files')

        control_checksums: dict[str, str] = {
            "ITEM.DAT": "a9d5684644fdef03414d1a39fff479ed3294beb64213f47faa30a1d8a5b11666",
            "ITEMSORT.DAT": "5525039567d1f4385a37d2c26e34a309fea1486d99fb644482e5a5932dc0d6aa",
        }

        for file in os.listdir(out_dir):
            file_path: str = os.path.join(out_dir, file)
            self.assertIs(os.path.isfile(file_path), True, msg=f"{file} should exist")

            file_hash: str = ""
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                f.close()

            self.assertEqual(file_hash, control_checksums[file], msg=f"{file} does not match checksum")

    @unittest.skip("skipping this test")
    def test_extract_npc(self):
        """FPS4 Extraction Test: npc.svo"""
        target = os.path.join(paths.CONTROL_DIR, "npc.svo")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_npc")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "npc.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 294, msg='Expected 294 output file')

    def test_extract_room(self):
        """FPS4 Extraction Test: AHO_I00_02.tlzc"""
        target = os.path.join(paths.CONTROL_DIR, "AHO_I00_02.tlzc")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_room")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "AHO_I00_02.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 1, msg='Expected 1 output files')

        checksum: str = "25277e1761703e7ad12f27ff5973aee1f98cb3ab10a3902827e49f71c775fda6"
        file_hash: str = ""
        with open(os.path.join(out_dir, os.listdir(out_dir)[0]), "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum, msg=f"{out_dir} does not match checksum")

    @unittest.skip("skipping this test")
    def test_pack_T8BTMA(self):
        """FPS4 Pack Test: 0004 (BTL_PACK.DAT)"""
        manifest = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "T8BTMA.json")
        assert os.path.isfile(manifest)

        output = os.path.join(paths.ARTIFACTS_DIR, "pck_T8BTM8", "0004")

        fps4.pack_from_manifest(output, manifest)

        self.assertIs(os.path.isfile(output), True, msg=f"{output} was failed to be created")

    @unittest.skip("skipping this test")
    def test_pack_btl_pack(self):
        """FPS4 Pack Test: BTL_PACK.DAT"""
        manifest = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "BTL_PACK.json")
        assert os.path.isfile(manifest)

        output = os.path.join(paths.ARTIFACTS_DIR, "pck_BTL_PACK", "BTL_PACK.DAT")

        fps4.pack_from_manifest(output, manifest)

        self.assertIs(os.path.isfile(output), True, msg=f"{output} was failed to be created")

        checksum: str = "2587565b2581041d063f8eaf8346bf13cbc52c60b3e194f6e6eb41ea6771350f"
        file_hash: str = ""
        with open(output, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum, msg=f"{output} does not match checksum")

    def test_pack_room(self):
        """FPS4 Pack Test: 0004 (AHO_I00_02.tlzc)"""
        manifest = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "AHO_I00_02.json")
        assert os.path.isfile(manifest)

        output = os.path.join(paths.ARTIFACTS_DIR, "pck_room", "AHO_I00_02.tlzc")

        fps4.pack_from_manifest(output, manifest)

        self.assertIs(os.path.isfile(output), True, msg=f"{output} was failed to be created")

        checksum: str = "c27fc06e74e55d41defc46d2eaaeece29dc54ae88b0af9712441d4a61c3b7940"
        file_hash: str = ""
        with open(output, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum, msg=f"{output} does not match checksum")

if __name__ == '__main__':
    unittest.main(verbosity=2)