import unittest

from services.database_service import DatabaseService


class DatabaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DatabaseService()

    def test_rejects_untrusted_procedure_name(self):
        with self.assertRaises(ValueError):
            self.service.execute_procedure("usp_Good; DROP TABLE users")

    def test_rejects_untrusted_parameter_name(self):
        with self.assertRaises(ValueError):
            self.service.execute_procedure(
                "usp_Good", [("@UserKey; DELETE", "test-user-1")]
            )

    def test_names_result_sets_and_fills_missing_sections(self):
        result = self.service.name_result_sets([[{"id": 1}]], ("first", "second"))

        self.assertEqual(result["first"], [{"id": 1}])
        self.assertEqual(result["second"], [])

    def test_last_result_selects_final_procedure_output(self):
        self.service.execute_procedure = lambda *args, **kwargs: [
            [{"helper": True}],
            [{"saved_id": 42}],
        ]

        result = self.service.last_result("usp_Good")

        self.assertEqual(result, [{"saved_id": 42}])


if __name__ == "__main__":
    unittest.main()
