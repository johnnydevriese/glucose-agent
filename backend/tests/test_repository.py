import tempfile
import unittest
from pathlib import Path

from glucose_agent.repository import GlucoseRepository


class RepositoryTests(unittest.TestCase):
    def test_new_repository_starts_with_seed_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = GlucoseRepository(Path(tmpdir) / "state.json")
            readings = repo.list_readings()
            self.assertGreaterEqual(len(readings), 5)


if __name__ == "__main__":
    unittest.main()
