"""Unit tests for api.py backend service"""
import unittest
from api import TimetableAPIService


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.service = TimetableAPIService()

    def test_service_generate_dsatur(self):
        res = self.service.generate({"algorithm": "DSATUR"})
        self.assertTrue(res["success"])
        self.assertEqual(res["validation"]["error_count"], 0)
        self.assertGreater(res["stats"]["slots_used"], 0)
        self.assertIn("timetable", res)
        self.assertIn("graph_visualization", res)

    def test_service_workload(self):
        res = self.service.get_workload()
        self.assertIn("faculty_workload", res)
        self.assertIn("heatmap", res)
        self.assertEqual(len(res["heatmap"]), 30)

    def test_service_schedules_all_grades_within_weekly_caps(self):
        result = self.service.generate()
        grades = {division["year_id"] for division in self.service.raw_data["divisions"]}
        self.assertEqual(grades, {"FY", "SY", "TY", "LY"})
        self.assertEqual(result["stats"]["total_placed"], result["stats"]["total_sessions"])
        self.assertEqual(result["stats"]["unplaced_count"], 0)
        self.assertEqual(result["validation"]["error_count"], 0)
        self.assertTrue(all(not member["over_cap"] for member in self.service.get_faculty_hours()["faculty"]))
        self.assertTrue(all(len(entry["slot_ids"]) == 2 for entry in result["timetable"]["entries"] if entry["is_lab"]))


if __name__ == "__main__":
    unittest.main()
