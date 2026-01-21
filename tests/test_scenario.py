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

        out_dir = os.path.join(paths.ARTIFACTS_DIR, "scenario_ENG")

        scenario.extract(target, out_dir)

        output_count: int = len(os.listdir(out_dir))
        self.assertEqual(output_count, 1466)

if __name__ == '__main__':
    unittest.main()