import unittest
import hashlib
import shutil
import os

from settings_test import paths
from libvespy import fps4


class TestFPS4(unittest.TestCase):
    def test_extract_btl(self):
        """FPS4 Extraction Test: btl.svo"""
        target = os.path.join(paths.CONTROL_DIR, 'btl.svo')
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, 'btl')
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, '.manifest', 'btl.json')

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 3)

        control_checksums: dict[str, str] = {
            "BTL_EFFECT.DAT": "5d75b49a0129e3e6eb2dc17fdf1923d70d29f592cc5790387c93889036eb3af5",
            "BTL_EFFECT.DAV": "c20827f1e76c7a1ba55b3e320171ecbca45da94fa022d73aab2d1cf3793e3452",
            "BTL_PACK.DAT": "2587565b2581041d063f8eaf8346bf13cbc52c60b3e194f6e6eb41ea6771350f"
        }

        for file in os.listdir(out_dir):
            with open(os.path.join(out_dir, file), 'rb') as f:
                if file not in control_checksums: continue

                file_hash = hashlib.sha256(f.read()).hexdigest()
                self.assertEqual(file_hash, control_checksums[file])

                f.close()

    def test_extract_btl_pack(self):
        """FPS4 Extraction Test: BTL_PACK.DAT"""
        target = os.path.join(paths.CONTROL_DIR, "BTL_PACK.DAT")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "BTL_PACK")
        manifest_dir = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "BTL_PACK.json")

        fps4.extract(target, out_dir, manifest_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 24)

    def test_pack_btl_pack(self):
        """FPS4 Pack Test: BTL_PACK.DAT"""
        manifest = os.path.join(paths.ARTIFACTS_DIR, ".manifest", "BTL_PACK.json")
        assert os.path.isfile(manifest)

        output = os.path.join(paths.ARTIFACTS_DIR, "btl_pack.pck", "BTL_PACK.DAT")

        fps4.pack_from_manifest(output, manifest)

        self.assertIs(os.path.isfile(output), True)

if __name__ == '__main__':
    # Create clean artifact folder
    contents: list[str] = os.listdir(paths.ARTIFACTS_DIR)
    for content in contents:
        if os.path.isfile(os.path.join(paths.ARTIFACTS_DIR, content)):
            os.remove(os.path.join(paths.ARTIFACTS_DIR, content))
        elif os.path.isdir(os.path.join(paths.ARTIFACTS_DIR, content)):
            shutil.rmtree(os.path.join(paths.ARTIFACTS_DIR, content))

    unittest.main(verbosity=2)