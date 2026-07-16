import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from chronos.core.checkpoint import init_chronos, create_checkpoint, get_db_path, get_chronos_dir
from chronos.core.db import DB
from chronos.core.config import ConfigManager
from chronos.core.status import get_status
from chronos.core.timeline import get_timeline
from chronos.core.diff import diff_checkpoints
from chronos.core.restore import plan_restore, restore_checkpoint

class TestChronos(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for each test
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        # Restore cwd and clean up
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_init_chronos(self):
        msg = init_chronos(self.test_dir)
        self.assertIn("Initialized empty Chronos repository", msg)
        self.assertTrue(os.path.exists(get_chronos_dir(self.test_dir)))
        self.assertTrue(os.path.exists(get_db_path(self.test_dir)))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, ".gitignore")))

    def test_checkpoint_and_restore(self):
        init_chronos(self.test_dir)

        # Create a mock source file
        src_file = os.path.join(self.test_dir, "app.py")
        with open(src_file, "w") as f:
            f.write("print('hello world')")

        # Create first checkpoint
        cp1_id = create_checkpoint(self.test_dir, "Initial commit")
        self.assertTrue(cp1_id.startswith("cp_"))

        # Verify db tracking
        db = DB(get_db_path(self.test_dir))
        latest = db.get_latest_checkpoint()
        self.assertEqual(latest["id"], cp1_id)
        self.assertEqual(latest["message"], "Initial commit")

        tracked = db.get_tracked_files(cp1_id)
        tracked_filepaths = [t["filepath"] for t in tracked]
        self.assertIn("app.py", tracked_filepaths)

        # Modify file and create second checkpoint
        with open(src_file, "w") as f:
            f.write("print('hello back')")

        cp2_id = create_checkpoint(self.test_dir, "Second commit")

        # Verify status shows no files modified now that it is checkpointed
        status_data = get_status(self.test_dir)
        self.assertEqual(len(status_data["files"]["modified"]), 0)

        # Let's modify file again (local dirty state)
        with open(src_file, "w") as f:
            f.write("print('dirty')")

        # Verify status detects modification
        status_data = get_status(self.test_dir)
        self.assertIn("app.py", status_data["files"]["modified"])

        # Compare diff between cp1 and cp2
        diff_data = diff_checkpoints(self.test_dir, cp1_id, cp2_id)
        self.assertIn("app.py", diff_data["files"]["modified"])

        # Restore back to cp1
        restore_checkpoint(self.test_dir, cp1_id)

        # Verify file content is back to initial version
        with open(src_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "print('hello world')")

    def test_package_detection(self):
        init_chronos(self.test_dir)

        # Create a mock requirements.txt
        req_file = os.path.join(self.test_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests==2.31.0\npytest\n")

        # Create checkpoint
        cp_id = create_checkpoint(self.test_dir, "Check packages")

        db = DB(get_db_path(self.test_dir))
        pkgs = db.get_packages(cp_id)

        # Should have found python/pip packages from requirements.txt
        pip_pkgs = [p for p in pkgs if p["manager"] == "pip"]
        self.assertTrue(len(pip_pkgs) >= 2)

        # requests has version, pytest has 'any'
        req_pkg = [p for p in pip_pkgs if p["name"] == "requests"][0]
        self.assertEqual(req_pkg["version"], "2.31.0")

if __name__ == "__main__":
    unittest.main()
