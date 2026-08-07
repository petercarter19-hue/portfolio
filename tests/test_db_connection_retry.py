import importlib
import inspect
import os
import unittest
from unittest import mock


import db
from mssql_python import Connection, Cursor


class DatabaseConnectionBudgetTests(unittest.TestCase):
    def setUp(self):
        self.environment = mock.patch.dict(
            os.environ,
            {"AZURE_SQL_CONNECTIONSTRING": "Server=test;Database=test"},
            clear=False,
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_default_connection_budget_is_user_appropriate(self):
        self.assertLessEqual(db.SQL_CONNECT_MAX_WAIT_SECONDS, 11)
        self.assertEqual(db.SQL_CONNECT_ATTEMPTS, 2)
        self.assertEqual(db.SQL_CONNECT_TIMEOUT_SECONDS, 5)
        self.assertEqual(db.SQL_QUERY_TIMEOUT_SECONDS, 15)

    def test_pinned_driver_propagates_connection_timeout_to_each_cursor(self):
        source = inspect.getsource(Connection.cursor)
        self.assertIn("Cursor(self, timeout=self._timeout)", source)
        self.assertEqual(inspect.signature(Cursor).parameters["timeout"].default, 0)

    @mock.patch("db.time.sleep")
    @mock.patch("db.connect")
    def test_one_transient_login_failure_is_retried_only_once(self, connect, sleep):
        connection = mock.Mock()
        connect.side_effect = [db.MssqlError("transient", "transient"), connection]

        result = db.get_connection()

        self.assertIs(result, connection)
        self.assertEqual(connect.call_count, 2)
        for call in connect.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 5)
        sleep.assert_called_once_with(0.25)
        self.assertEqual(connection.timeout, 15)
        connection.setautocommit.assert_called_once_with(True)
        connection.close()

    @mock.patch("db.time.sleep")
    @mock.patch("db.connect")
    def test_terminal_login_failure_stops_after_bounded_attempts(self, connect, sleep):
        connect.side_effect = db.MssqlError("unavailable", "unavailable")

        with self.assertRaises(db.MssqlError):
            db.get_connection()

        self.assertEqual(connect.call_count, 2)
        sleep.assert_called_once_with(0.25)

    def test_environment_overrides_are_clamped(self):
        with mock.patch.dict(
            os.environ,
            {
                "PEERSLATE_SQL_CONNECT_ATTEMPTS": "99",
                "PEERSLATE_SQL_CONNECT_TIMEOUT_SECONDS": "600",
                "PEERSLATE_SQL_CONNECT_RETRY_DELAY_SECONDS": "30",
                "PEERSLATE_SQL_QUERY_TIMEOUT_SECONDS": "600",
            },
        ):
            reloaded = importlib.reload(db)
            self.assertEqual(reloaded.SQL_CONNECT_ATTEMPTS, 2)
            self.assertEqual(reloaded.SQL_CONNECT_TIMEOUT_SECONDS, 10)
            self.assertEqual(reloaded.SQL_CONNECT_RETRY_DELAY_SECONDS, 1.0)
            self.assertEqual(reloaded.SQL_QUERY_TIMEOUT_SECONDS, 30)
            self.assertLessEqual(reloaded.SQL_CONNECT_MAX_WAIT_SECONDS, 21)
        importlib.reload(db)


if __name__ == "__main__":
    unittest.main()
