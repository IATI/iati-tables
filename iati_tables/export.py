import base64
import gzip
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from textwrap import dedent

from fastavro import parse_schema, writer
from google.cloud import bigquery
from google.cloud.bigquery.dataset import AccessEntry
from google.oauth2 import service_account
from sqlalchemy import text

from iati_tables.database import create_field_sql, get_engine, schema

output_dir = os.environ.get("IATI_TABLES_OUTPUT", ".")
output_path = pathlib.Path(output_dir)

logger = logging.getLogger(__name__)


def export_stats():
    logger.info("Exporting statistics")
    stats_file = output_path / "stats.json"

    with get_engine().begin() as connection:
        stats = {}

        results = connection.execute(text("SELECT * FROM metadata"))
        metadata = results.fetchone()
        stats["data_dump_updated_at"] = str(metadata.data_dump_updated_at)
        stats["updated"] = str(metadata.iati_tables_updated_at)

        results = connection.execute(
            text("SELECT to_json(_tables) as table FROM _tables order by table_order")
        )
        stats["tables"] = [row.table for row in results]

        fields = defaultdict(list)

        results = connection.execute(
            text(
                """
                SELECT table_name, to_json(_fields) as field_info
                FROM _fields
                ORDER BY table_name, field_order, field
                """
            )
        )

        for result in results:
            fields[result.table_name].append(result.field_info)

        stats["fields"] = fields

        stats_file.write_text(json.dumps(stats, indent=2))

        activities = [
            row.iatiidentifier
            for row in connection.execute(
                text("SELECT iatiidentifier from activity group by 1")
            )
        ]

        with gzip.open(
            str(output_path / "activities.json.gz"), "wt"
        ) as activities_file:
            json.dump(activities, activities_file)


def export_sqlite():
    logger.info("Exporting sqlite format")
    sqlite_file = output_path / "iati.sqlite"
    if sqlite_file.is_file():
        sqlite_file.unlink()
    datasette_file = output_path / "iati.db"
    if datasette_file.is_file():
        datasette_file.unlink()

    object_details = defaultdict(list)
    with tempfile.TemporaryDirectory() as tmpdirname, get_engine().begin() as connection:
        result = list(
            connection.execute(
                text(
                    "SELECT table_name, field, type FROM _fields order by  table_name, field_order, field"
                )
            )
        )
        for row in result:
            object_details[row.table_name].append(dict(name=row.field, type=row.type))

        indexes = []

        for object_type, object_details in object_details.items():
            target_object_type = re.sub("[^0-9a-zA-Z]+", "_", object_type.lower())
            if object_type == "transaction":
                target_object_type = "trans"

            fks = []

            for num, item in enumerate(object_details):
                name = item["name"]
                if name.startswith("_link"):
                    indexes.append(
                        f'CREATE INDEX "{target_object_type}_{name}" on "{target_object_type}"("{name}");'
                    )
                if name.startswith("_link_"):
                    foreign_table = name[6:]
                    if foreign_table == "transaction":
                        foreign_table = "trans"
                    if object_type == "activity":
                        continue
                    fks.append(
                        f',FOREIGN KEY("{name}") REFERENCES "{foreign_table}"(_link)'
                    )

            logger.debug(f"Importing table {object_type}")
            with open(f"{tmpdirname}/{object_type}.csv", "wb") as out:
                dbapi_conn = connection.connection
                copy_sql = f'COPY "{object_type.lower()}" TO STDOUT WITH (FORMAT CSV, FORCE_QUOTE *)'
                cur = dbapi_conn.cursor()
                cur.copy_expert(copy_sql, out)

            _, field_def = create_field_sql(object_details, sqlite=True)

            import_sql = f"""
            .mode csv
            CREATE TABLE "{target_object_type}" ({field_def} {' '.join(fks)}) ;
            .import '{tmpdirname}/{object_type}.csv' "{target_object_type}" """

            logger.debug(import_sql)

            subprocess.run(
                ["sqlite3", f"{sqlite_file}"],
                input=dedent(import_sql),
                text=True,
                check=True,
            )

            os.remove(f"{tmpdirname}/{object_type}.csv")

        with open(f"{tmpdirname}/fields.csv", "w") as csv_file:
            dbapi_conn = connection.connection
            copy_sql = 'COPY "_fields" TO STDOUT WITH (FORMAT CSV, FORCE_QUOTE *)'
            cur = dbapi_conn.cursor()
            cur.copy_expert(copy_sql, csv_file)

        import_sql = f"""
            .mode csv
            CREATE TABLE _fields (table_name TEXT, field TEXT, type TEXT, count INT, docs TEXT, field_order INT);
            .import {tmpdirname}/fields.csv "_fields" """

        subprocess.run(
            ["sqlite3", f"{sqlite_file}"],
            input=dedent(import_sql),
            text=True,
            check=True,
        )

        shutil.copy(sqlite_file, datasette_file)

        subprocess.run(
            ["sqlite3", f"{datasette_file}"],
            input="\n".join(indexes),
            text=True,
            check=True,
        )

        subprocess.run(["gzip", "-f", "-9", f"{datasette_file}"], check=True)
        subprocess.run(["gzip", "-fk", "-9", f"{sqlite_file}"], check=True)
        subprocess.run(
            ["zip", f"{output_path}/iati.sqlite.zip", f"{sqlite_file}"], check=True
        )


def export_csv():
    logger.info("Exporting CSV format")
    with get_engine().begin() as connection, zipfile.ZipFile(
        f"{output_dir}/iati_csv.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        result = list(connection.execute(text("SELECT table_name FROM _tables")))
        for row in result:
            csv_output_path = output_path / f"{row.table_name}.csv"
            with open(f"{csv_output_path}", "wb") as out:
                dbapi_conn = connection.connection
                copy_sql = f'COPY "{row.table_name.lower()}" TO STDOUT WITH CSV HEADER'
                cur = dbapi_conn.cursor()
                cur.copy_expert(copy_sql, out)

            zip_file.write(
                f"{output_dir}/{row.table_name}.csv",
                arcname=f"iati/{row.table_name}.csv",
            )
            csv_output_path.unlink()


def export_pgdump():
    logger.info("Exporting pg_dump format")
    subprocess.run(
        [
            "pg_dump",
            "--no-owner",
            "-f",
            f"{output_dir}/iati.custom.pg_dump",
            "-n",
            schema or "public",
            "-F",
            "c",
            os.environ["DATABASE_URL"],
        ],
        check=True,
    )
    cmd = f"""
       pg_dump --no-owner -n {schema or 'public'} {os.environ["DATABASE_URL"]} | gzip > {output_dir}/iati.dump.gz
    """
    subprocess.run(cmd, shell=True, check=True)


name_allowed_pattern = re.compile(r"[\W]+")


def create_avro_schema(object_type, object_details):
    fields = []
    schema = {"type": "record", "name": object_type, "fields": fields}
    for item in object_details:
        type = item["type"]
        if type == "number":
            type = "double"
        if type == "datetime":
            type = "string"

        field = {
            "name": name_allowed_pattern.sub("", item["name"]),
            "type": [type, "null"],
            "doc": item.get("description"),
        }

        if type == "array":
            field["type"] = [
                {"type": "array", "items": "string", "default": []},
                "null",
            ]

        fields.append(field)

    return schema


def generate_avro_records(result, object_details):
    cast_to_string = set(
        [field["name"] for field in object_details if field["type"] == "string"]
    )

    for row in result:
        new_object = {}
        for key, value in row.object.items():
            new_object[name_allowed_pattern.sub("", key)] = (
                str(value) if key in cast_to_string else value
            )
        yield new_object


def export_bigquery():
    logger.info("Exporting to BigQuery")
    json_acct_info = json.loads(base64.b64decode(os.environ["GOOGLE_SERVICE_ACCOUNT"]))

    credentials = service_account.Credentials.from_service_account_info(json_acct_info)

    client = bigquery.Client(credentials=credentials)

    with tempfile.TemporaryDirectory() as tmpdirname, get_engine().begin() as connection:
        dataset_id = "iati-tables.iati"
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "EU"

        dataset = client.create_dataset(dataset, timeout=30)

        access_entries = list(dataset.access_entries)
        access_entries.append(
            AccessEntry("READER", "specialGroup", "allAuthenticatedUsers")
        )
        dataset.access_entries = access_entries

        dataset = client.update_dataset(dataset, ["access_entries"])

        object_details = defaultdict(list)
        result = list(
            connection.execute(
                "SELECT table_name, field, type, docs FROM _fields order by table_name, field_order, field"
            )
        )

        for row in result:
            object_details[row.table_name].append(
                dict(name=row.field, type=row.type, description=row.docs)
            )

        for object_type, object_details in object_details.items():
            logger.info(f"Loading {object_type}")
            result = connection.execute(
                text(
                    f'SELECT to_jsonb("{object_type.lower()}") AS object FROM "{object_type.lower()}"'
                )
            )
            schema = create_avro_schema(object_type, object_details)

            with open(f"{tmpdirname}/{object_type}.avro", "wb") as out:
                writer(
                    out,
                    parse_schema(schema),
                    generate_avro_records(result, object_details),
                    validator=True,
                    codec="deflate",
                )

            table_id = f"{dataset_id}.{object_type}"

            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.AVRO
            )

            with open(f"{tmpdirname}/{object_type}.avro", "rb") as source_file:
                client.load_table_from_file(
                    source_file, table_id, job_config=job_config, size=None, timeout=5
                )


def export_all():
    export_stats()
    export_sqlite()
    export_csv()
    export_pgdump()
    try:
        export_bigquery()
    except Exception:
        logger.warning("Big query failed, proceeding anyway")
