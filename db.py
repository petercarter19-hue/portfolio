import logging
import os    # Reads environment variables
import re
import time
from datetime import date, datetime    # Handles SQL date and time values
from decimal import Decimal    # Handles SQL decimal values

from dotenv import load_dotenv    # Loads the local .env file
from mssql_python import Error as MssqlError
from mssql_python import connect    # Connects Python to Azure SQL


load_dotenv()    # Loads the protected connection string from .env

logger = logging.getLogger(__name__)

def _bounded_number(name, default, minimum, maximum, cast):
    """Read an operational timeout without permitting an unbounded wait."""

    try:
        value = cast(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return min(max(value, minimum), maximum)


SQL_CONNECT_ATTEMPTS = _bounded_number(
    "PEERSLATE_SQL_CONNECT_ATTEMPTS", 2, 1, 2, int
)
SQL_CONNECT_TIMEOUT_SECONDS = _bounded_number(
    "PEERSLATE_SQL_CONNECT_TIMEOUT_SECONDS", 5, 1, 10, int
)
SQL_CONNECT_RETRY_DELAY_SECONDS = _bounded_number(
    "PEERSLATE_SQL_CONNECT_RETRY_DELAY_SECONDS", 0.25, 0.0, 1.0, float
)
SQL_QUERY_TIMEOUT_SECONDS = _bounded_number(
    "PEERSLATE_SQL_QUERY_TIMEOUT_SECONDS", 15, 5, 30, int
)
SQL_CONNECT_MAX_WAIT_SECONDS = (
    SQL_CONNECT_ATTEMPTS * SQL_CONNECT_TIMEOUT_SECONDS
    + (SQL_CONNECT_ATTEMPTS - 1) * SQL_CONNECT_RETRY_DELAY_SECONDS
)


def normalize_connection_string(connection_string):
    """Remove Azure portal options that mssql-python does not accept."""

    connection_string = connection_string.replace(
        ".database.windows.net.database.windows.net",
        ".database.windows.net",
    )

    # Avoid splitting the complete connection string because a properly
    # escaped password may itself contain a semicolon.
    return re.sub(
        r"(?i)(^|;)\s*connection timeout\s*=\s*[^;]*(?=;|$)",
        r"\1",
        connection_string,
    )


def get_connection():
    """Open and return an Azure SQL connection.

    Production is continuously provisioned, so a dependency failure must fail
    quickly enough to preserve web availability. Retry only connection
    establishment once; a stored procedure or other operation is never
    replayed. Import-time bounds cap the total login budget even if an
    environment value is stale or mistyped.
    """

    connection_string = os.getenv("AZURE_SQL_CONNECTIONSTRING")    # Reads the connection string

    if not connection_string:
        raise RuntimeError(
            "AZURE_SQL_CONNECTIONSTRING is missing. Check the root .env file."
        )

    normalized_connection_string = normalize_connection_string(connection_string)

    for attempt in range(1, SQL_CONNECT_ATTEMPTS + 1):
        connection = None
        try:
            connection = connect(
                normalized_connection_string,
                timeout=SQL_CONNECT_TIMEOUT_SECONDS,
            )
            # Pinned mssql-python 1.11 propagates Connection.timeout into every
            # Cursor it creates, and Cursor applies it as
            # SQL_ATTR_QUERY_TIMEOUT before execution. Keep this assignment
            # before any cursor can be created.
            connection.timeout = SQL_QUERY_TIMEOUT_SECONDS
            connection.setautocommit(True)
            return connection
        except MssqlError:
            if connection is not None:
                try:
                    connection.close()
                except MssqlError:
                    pass

            if attempt >= SQL_CONNECT_ATTEMPTS:
                raise

            logger.warning(
                "Azure SQL connection attempt %s/%s failed; retrying after "
                "the bounded transient-failure delay.",
                attempt,
                SQL_CONNECT_ATTEMPTS,
            )
            time.sleep(SQL_CONNECT_RETRY_DELAY_SECONDS)


def serialize_sql_value(value):
    """Convert SQL values into JSON-safe Python values."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()    # Converts dates into readable text

    if isinstance(value, Decimal):
        return float(value)    # Converts decimals into JSON-compatible numbers

    if isinstance(value, bytes):
        return value.hex()    # Converts binary values into text

    return value


def fetch_current_result_set(cursor):
    """Convert the current SQL result grid into dictionaries."""

    if cursor.description is None:
        return []

    column_names = [column[0] for column in cursor.description]    # Gets column names
    result_rows = []

    for row in cursor.fetchall():
        result_rows.append(
            {
                column_name: serialize_sql_value(value)
                for column_name, value in zip(column_names, row)
            }
        )

    return result_rows


def fetch_all_result_sets(cursor):
    """Read every result grid returned by a stored procedure."""

    result_sets = []

    while True:
        if cursor.description is not None:
            result_sets.append(fetch_current_result_set(cursor))

        if not cursor.nextset():
            break

    return result_sets
