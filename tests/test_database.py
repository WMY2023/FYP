import os
import tempfile
import unittest
from pathlib import Path


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(self.temp_dir.name) / "test.db")
        import database
        self.database = database
        database.init_database()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_PATH", None)

    def test_report_and_communication_are_persisted(self):
        report_id = self.database.save_patient_report("PT-1", "CBC", "Hemoglobin 12")
        self.database.save_communication("PT-1", report_id, "assistant", "Please discuss this with your doctor.", "專業簡潔", "一般民眾")
        self.assertEqual(self.database.list_reports("PT-1")[0]["id"], report_id)
        self.assertEqual(len(self.database.list_communications("PT-1", report_id)), 1)

    def test_reference_is_chunked_with_overlap(self):
        count = self.database.save_reference("Guide", "Clinic", "section 1", "blood pressure " * 100, chunk_size=100, overlap=20)
        self.assertGreater(count, 1)
        self.assertEqual(len(self.database.list_references()), count)

    def test_references_are_separated_by_type(self):
        self.database.save_reference("Style guide", "Clinic", "section 1", "warm and reassuring", reference_type="tone")
        self.database.save_reference("Medical guide", "Clinic", "section 1", "blood pressure", reference_type="medical")
        self.assertEqual(len(self.database.list_references("tone")), 1)
        self.assertEqual(len(self.database.list_references("medical")), 1)

    def test_reference_can_be_deleted_with_all_chunks(self):
        self.database.save_reference("Guide", "Clinic", "section 1", "blood pressure " * 100, chunk_size=100, overlap=20)
        deleted = self.database.delete_reference("Guide", "Clinic", "section 1", "medical")
        self.assertGreater(deleted, 1)
        self.assertEqual(self.database.list_references(), [])


if __name__ == "__main__":
    unittest.main()
