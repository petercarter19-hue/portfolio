"""Reusable, parameterized access to PeerSlate Azure SQL procedures."""

import re

from db import fetch_all_result_sets, get_connection


_PROCEDURE_NAME = re.compile(r"^usp_[A-Za-z0-9_]+$")
_PARAMETER_NAME = re.compile(r"^@[A-Za-z][A-Za-z0-9_]*$")


class DatabaseServiceError(RuntimeError):
    """Raised when a database operation cannot be completed safely."""


class DatabaseService:
    """Execute known stored procedures with positional parameter binding."""

    def execute_procedure(self, procedure_name, parameters=None):
        if not _PROCEDURE_NAME.fullmatch(procedure_name):
            raise ValueError("Invalid stored procedure name.")

        bound_parameters = list(parameters or [])
        assignments = []
        values = []

        for parameter_name, value in bound_parameters:
            if not _PARAMETER_NAME.fullmatch(parameter_name):
                raise ValueError("Invalid stored procedure parameter name.")

            assignments.append(f"{parameter_name} = ?")
            values.append(value)

        statement = f"EXEC dbo.{procedure_name}"
        if assignments:
            statement = f"{statement} {', '.join(assignments)}"

        try:
            with get_connection() as connection:
                cursor = connection.cursor()
                if values:
                    cursor.execute(statement, tuple(values))
                else:
                    cursor.execute(statement)
                return fetch_all_result_sets(cursor)
        except Exception as error:
            raise DatabaseServiceError(
                f"Database procedure {procedure_name} failed."
            ) from error

    def first_result(self, procedure_name, parameters=None):
        result_sets = self.execute_procedure(procedure_name, parameters)
        return result_sets[0] if result_sets else []

    def first_row(self, procedure_name, parameters=None):
        rows = self.first_result(procedure_name, parameters)
        return rows[0] if rows else None

    def last_result(self, procedure_name, parameters=None):
        result_sets = self.execute_procedure(procedure_name, parameters)
        return result_sets[-1] if result_sets else []

    def last_row(self, procedure_name, parameters=None):
        rows = self.last_result(procedure_name, parameters)
        return rows[0] if rows else None

    @staticmethod
    def name_result_sets(result_sets, names):
        result_names = list(names)
        return {
            name: result_sets[index] if index < len(result_sets) else []
            for index, name in enumerate(result_names)
        }


database_service = DatabaseService()
