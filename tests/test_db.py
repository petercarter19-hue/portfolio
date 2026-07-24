import os
import unittest
from unittest.mock import Mock, patch

from mssql_python import DatabaseError

import db


class DatabaseConnectionTests(unittest.TestCase):
    def database_error(self):
        return DatabaseError("test driver error", "test database error")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_connection_string_fails_without_calling_driver(self):
        with patch("db.connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "AZURE_SQL_CONNECTIONSTRING"):
                db.get_connection()

        connect.assert_not_called()

    @patch.dict(
        os.environ,
        {"AZURE_SQL_CONNECTIONSTRING": "Server=test;Database=peerslate;"},
        clear=True,
    )
    @patch("db.time.sleep")
    @patch("db.connect")
    def test_transient_connect_failure_retries_before_any_sql(self, connect, sleep):
        connection = Mock()
        connect.side_effect = [self.database_error(), connection]

        result = db.get_connection()

        self.assertIs(result, connection)
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(
            connect.call_args_list[0].kwargs["timeout"],
            db.SQL_CONNECT_TIMEOUT_SECONDS,
        )
        sleep.assert_called_once_with(db.SQL_CONNECT_RETRY_DELAY_SECONDS)
        connection.setautocommit.assert_called_once_with(True)
        connection.cursor.assert_not_called()

    @patch.dict(
        os.environ,
        {"AZURE_SQL_CONNECTIONSTRING": "Server=test;Database=peerslate;"},
        clear=True,
    )
    @patch("db.time.sleep")
    @patch("db.connect")
    def test_exhausted_connect_retries_raise_last_driver_error(self, connect, sleep):
        first_error = self.database_error()
        last_error = self.database_error()
        connect.side_effect = [first_error, last_error]

        with self.assertRaises(DatabaseError) as raised:
            db.get_connection()

        self.assertIs(raised.exception, last_error)
        self.assertEqual(connect.call_count, db.SQL_CONNECT_ATTEMPTS)
        sleep.assert_called_once_with(db.SQL_CONNECT_RETRY_DELAY_SECONDS)


if __name__ == "__main__":
    unittest.main()
