import os    # Reads environment variables
from datetime import date, datetime    # Handles SQL date and time values
from decimal import Decimal    # Handles SQL decimal values

from dotenv import load_dotenv    # Loads the local .env file
from mssql_python import connect    # Connects Python to Azure SQL


load_dotenv()    # Loads the protected connection string from .env


def get_connection():
    """Open and return an Azure SQL connection."""

    connection_string = os.getenv("AZURE_SQL_CONNECTIONSTRING")    # Reads the connection string

    if not connection_string:
        raise RuntimeError(
            "AZURE_SQL_CONNECTIONSTRING is missing. Check the root .env file."
        )

    connection = connect(connection_string)    # Opens the Azure SQL connection
    connection.setautocommit(True)    # Commits stored-procedure actions automatically

    return connection


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