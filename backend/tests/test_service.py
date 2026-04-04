import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from glucose_agent.agents import AgentSuite
from glucose_agent.repository import GlucoseRepository
from glucose_agent.service import GlucoseService
from glucose_agent.settings import AppSettings


class ServiceTests(unittest.TestCase):
    def test_confirm_flow_updates_history_and_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = GlucoseRepository(Path(tmpdir) / "state.json")
            agents = AgentSuite(settings=AppSettings())
            service = GlucoseService(repo, agents)
            session_id = "test-session"

            events = asyncio.run(
                service.handle_message(session_id, "My glucose was 110 today fasting")
            )
            self.assertEqual(events[0].type, "reading_extracted")

            confirmed = asyncio.run(service.confirm_reading(session_id, events[0].reading))
            event_types = [event.type for event in confirmed]
            self.assertEqual(event_types, ["message", "history_update", "stats_update"])
            self.assertTrue(
                any(reading.glucose_level == 110.0 for reading in confirmed[1].readings)
            )
            self.assertGreaterEqual(confirmed[2].stats.total_readings, 1)


if __name__ == "__main__":
    unittest.main()
