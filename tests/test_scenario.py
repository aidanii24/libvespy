import hashlib
import unittest
import shutil
import os

from settings_test import paths
from libvespy import scenario

class TestScenario(unittest.TestCase):
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

    def test_scenario_extract(self):
        """Scenario Extraction Test: scenario_ENG.dat"""
        target = os.path.join(paths.CONTROL_DIR, "scenario_ENG.dat")
        assert os.path.isfile(target)

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "ext_scenario_ENG")

        scenario.extract(target, out_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 1466)

    def test_scenario_pack(self):
        """Scenario Pack Test: scenario_ENG.dat"""
        target = os.path.join(paths.ARTIFACTS_DIR, "ext_scenario_ENG")
        output = os.path.join(paths.ARTIFACTS_DIR, "pck_scenario_ENG.dat")

        scenario.pack(target, output)

        self.assertIs(os.path.isfile(output), True)

        checksum: str = "90a1e41ae829ba7f05e289aaba87cb4699e3ed27acc9448985f6f91261da8e2d"
        file_hash: str = ""
        with open(output, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            f.close()

        self.assertEqual(file_hash, checksum)

if __name__ == '__main__':
    unittest.main()