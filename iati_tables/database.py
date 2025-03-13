import logging
import os
from typing import Any

from sqlalchemy import Engine, create_engine, text

logger = logging.getLogger(__name__)


schema = os.environ.get("IATI_TABLES_SCHEMA")


def get_engine(db_uri: Any = None, pool_size: int = 1) -> Engine:
    if not db_uri:
        db_uri = os.environ["DATABASE_URL"]

    connect_args = {}

    if schema:
        connect_args = {"options": f"-csearch_path={schema}"}

    return create_engine(db_uri, pool_size=pool_size, connect_args=connect_args)


def create_field_sql(object_details, sqlite=False):
    fields = []
    lowered_fields = set()
    fields_with_type = []
    for num, item in enumerate(object_details):
        name = item["name"]

        if sqlite and name.lower() in lowered_fields:
            name = f'"{name}_{num}"'

        type = item["type"]
        if type == "number":
            field = f'"{name}" numeric'
        elif type == "array":
            field = f'"{name}" JSONB'
        elif type == "boolean":
            field = f'"{name}" boolean'
        elif type == "datetime":
            field = f'"{name}" timestamp'
        else:
            field = f'"{name}" TEXT'

        lowered_fields.add(name.lower())
        fields.append(f'x."{name}"')
        fields_with_type.append(field)

    return ", ".join(fields), ", ".join(fields_with_type)


def _create_table(table, con, sql, **params):
    logger.debug(f"Creating table: {table}")
    con.execute(
        text(
            f"""
            DROP TABLE IF EXISTS "{table}";
            CREATE TABLE "{table}" AS {sql};
            """
        ),
        {**params},
    )


def create_table(table, sql, **params):
    engine = get_engine()
    with engine.begin() as con:
        _create_table(table.lower(), con, sql, **params)
