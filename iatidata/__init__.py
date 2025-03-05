import base64
import concurrent.futures
import functools
import gzip
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import traceback
import zipfile
from collections import defaultdict
from datetime import datetime
from io import StringIO
from itertools import islice
from textwrap import dedent
from typing import Any, Iterator, Optional, OrderedDict

import iatikit
import requests
import xmlschema
from fastavro import parse_schema, writer
from google.cloud import bigquery
from google.cloud.bigquery.dataset import AccessEntry
from google.oauth2 import service_account
from lxml import etree
from sqlalchemy import Engine, column, create_engine, insert, table, text

from iatidata import sort_iati

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

this_dir = pathlib.Path(__file__).parent.resolve()

output_dir = os.environ.get("IATI_TABLES_OUTPUT", ".")

schema = os.environ.get("IATI_TABLES_SCHEMA")

s3_destination = os.environ.get("IATI_TABLES_S3_DESTINATION", "-")

output_path = pathlib.Path(output_dir)

VERSION_1_TRANSFORMS = {
    "activity": etree.XSLT(etree.parse(str(this_dir / "iati-activities.xsl"))),
    "organisation": etree.XSLT(etree.parse(str(this_dir / "iati-organisations.xsl"))),
}


def get_engine(db_uri: Any = None, pool_size: int = 1) -> Engine:
    if not db_uri:
        db_uri = os.environ["DATABASE_URL"]

    connect_args = {}

    if schema:
        connect_args = {"options": f"-csearch_path={schema}"}

    return create_engine(db_uri, pool_size=pool_size, connect_args=connect_args)


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


def create_raw_tables():
    engine = get_engine()
    with engine.begin() as connection:
        for filetype in ["activity", "organisation"]:
            table_name = f"_raw_{filetype}"
            logger.debug(f"Creating table: {table_name}")
            connection.execute(
                text(
                    f"""
                    DROP TABLE IF EXISTS {table_name};
                    CREATE TABLE {table_name}(
                        id SERIAL, prefix TEXT, dataset TEXT, filename TEXT, error TEXT, version TEXT, object JSONB
                    );
                    """
                )
            )


@functools.lru_cache
def get_xml_schema(filetype: str) -> xmlschema.XMLSchema10:
    if filetype == "activity":
        return xmlschema.XMLSchema(
            str(
                pathlib.Path()
                / "__iatikitcache__/standard/schemas/203/iati-activities-schema.xsd"
            )
        )
    else:
        return xmlschema.XMLSchema(
            str(
                pathlib.Path()
                / "__iatikitcache__/standard/schemas/203/iati-organisations-schema.xsd"
            )
        )


def get_standard(refresh=False):
    if not (pathlib.Path() / "__iatikitcache__").is_dir() or refresh:
        logger.info("Downloading standard")
        iatikit.download.standard()
    else:
        logger.info("Not refreshing standard")


def get_registry(refresh=False):
    if not (pathlib.Path() / "__iatikitcache__").is_dir() or refresh:
        logger.info("Downloading registry data")
        iatikit.download.data()
    else:
        logger.info("Not refreshing registry data")
    return iatikit.data()


def extract(refresh: bool = False) -> None:
    get_standard(refresh)
    get_registry(refresh)


def flatten_schema_docs(cur, path=""):
    for field, value in cur.items():
        info = value.get("info")
        docs = info.get("docs", "")
        yield f"{path}{field}", docs
        for attribute, attribute_docs in info.get("attributes", {}).items():
            yield f"{path}{field}_{attribute}", attribute_docs

        yield from flatten_schema_docs(value.get("properties", {}), f"{path}{field}_")


class IATISchemaWalker(sort_iati.IATISchemaWalker):
    def __init__(self):
        self.tree = etree.parse(
            str(
                pathlib.Path()
                / "__iatikitcache__/standard/schemas/203/iati-activities-schema.xsd"
            )
        )
        self.tree2 = etree.parse(
            str(
                pathlib.Path() / "__iatikitcache__/standard/schemas/203/iati-common.xsd"
            )
        )


def get_schema_docs():
    schema_docs = IATISchemaWalker().create_schema_docs("iati-activity")

    schema_docs_lookup = {}
    for num, (field, doc) in enumerate(flatten_schema_docs(schema_docs)):
        field = field.replace("-", "")
        # leave some space for extra fields at the start
        schema_docs_lookup[field] = [num + 10, doc]

    return schema_docs_lookup


def get_sorted_schema_dict():
    schema_dict = IATISchemaWalker().create_schema_dict("iati-activity")
    return schema_dict


def sort_iati_element(
    element: etree._Element, schema_subdict: OrderedDict[str, OrderedDict]
) -> None:
    """
    Sort the given elements children according to the order of schema_subdict.
    """

    def sort(x: etree._Element) -> int:
        try:
            return list(schema_subdict.keys()).index(x.tag)
        except ValueError:
            # make sure non schema elements go to the end
            return 9999

    children = list(element)
    for child in children:
        element.remove(child)
    for child in sorted(children, key=sort):
        element.append(child)
        subdict = schema_subdict.get(child.tag)
        if subdict:
            sort_iati_element(child, subdict)


ALL_CODELIST_LOOKUP = {}


def get_codelists_lookup():
    mapping_file = (
        pathlib.Path()
        / "__iatikitcache__/standard/codelist_mappings/203/activity-mappings.json"
    )
    mappings_list = json.loads(mapping_file.read_text())

    mappings = defaultdict(list)

    for mapping in mappings_list:
        path = tuple(mapping["path"][16:].replace("-", "").split("/"))
        mappings[mapping["codelist"]].append(path)

    mappings.pop("Version")

    mappings["Country"] = [
        ("transaction", "recipientcountry", "@code"),
        ("recipientcountry", "@code"),
    ]

    codelists_dir = pathlib.Path() / "__iatikitcache__/standard/codelists"

    for codelist_file in codelists_dir.glob("*.json"):
        codelist = json.loads(codelist_file.read_text())
        attributes = codelist.get("attributes")
        data = codelist.get("data")
        if not attributes or not data:
            continue

        codelist_name = attributes["name"]
        paths = mappings[codelist_name]

        for path in paths:
            for codelist_value, info in data.items():
                value_name = info.get("name", codelist_value)
                ALL_CODELIST_LOOKUP[(path, codelist_value)] = value_name


def parse_dataset(
    dataset: iatikit.Dataset,
) -> Iterator[tuple[dict[str, Any], list[xmlschema.XMLSchemaValidationError]]]:
    try:
        dataset_etree = dataset.etree.getroot()
    except Exception:
        logger.debug(f"Error parsing XML for dataset '{dataset.name}'")
        return

    print('dataset_etree', dataset_etree)
    version = dataset_etree.get("version", "1.01")
    print('dataset_etree version', version)

    if version.startswith("1"):
        logger.debug(f"Transforming v1 {dataset.filetype} file")
        dataset_etree = VERSION_1_TRANSFORMS[dataset.filetype](dataset_etree).getroot()
        print('dataset_etree in version starts with 1', dataset_etree)

    parent_element_name = (
        "iati-organisations"
        if dataset.filetype == "organisation"
        else "iati-activities"
    )
    child_element_name = f"iati-{dataset.filetype}"
    print('child_element_name', child_element_name)
    if 'zoa-activities.xml' in dataset.data_path:
        print('zoa-activities.xml return')
        return
    else:
        for child_element in dataset_etree.findall(child_element_name):
            sort_iati_element(child_element, get_sorted_schema_dict())
            parent_element = etree.Element(parent_element_name, version=version)
            parent_element.append(child_element)

            xmlschema_to_dict_result: tuple[dict[str, Any], list[Any]] = xmlschema.to_dict(
                parent_element,  # type: ignore
                schema=get_xml_schema(dataset.filetype),
                validation="lax",
                decimal_type=float,
            )
            parent_dict, error = xmlschema_to_dict_result
            child_dict = parent_dict.get(child_element_name, [{}])[0]
            yield child_dict, error


def csv_file_to_db(csv_fd):
    engine = get_engine()
    with engine.begin() as connection:
        dbapi_conn = connection.connection
        copy_sql = "COPY _all_activities(prefix, dataset, filename, error, version, activity) FROM STDIN WITH CSV"
        cur = dbapi_conn.cursor()
        cur.copy_expert(copy_sql, csv_fd)


def load_dataset(dataset: iatikit.Dataset) -> None:
    if not dataset.data_path:
        logger.warn(f"Dataset '{dataset}' not found")
        return

    print('dataset data_path', dataset.data_path)
    path = pathlib.Path(dataset.data_path)
    print('dataset', path)
    prefix, filename = path.parts[-2:]

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            insert(
                table(
                    f"_raw_{dataset.filetype}",
                    column("prefix"),
                    column("dataset"),
                    column("filename"),
                    column("error"),
                    column("version"),
                    column("object"),
                )
            ).values(
                [
                    {
                        "prefix": prefix,
                        "dataset": dataset.name,
                        "filename": filename,
                        "error": "\n".join(
                            [f"{error.reason} at {error.path}" for error in errors]
                        ),
                        "version": dataset.version,
                        "object": json.dumps(object),
                    }
                    for object, errors in parse_dataset(dataset)
                ]
            )
        )

    engine.dispose()


def create_database_schema():
    if schema:
        engine = get_engine()
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    DROP schema IF EXISTS {schema} CASCADE;
                    CREATE schema {schema};
                    """
                )
            )


def load(processes: int, sample: Optional[int] = None) -> None:
    create_database_schema()
    create_raw_tables()

    logger.info(
        f"Loading {len(list(islice(iatikit.data().datasets, sample)))} datasets into database"
    )
    datasets_sample = islice(iatikit.data().datasets, sample)

    with concurrent.futures.ProcessPoolExecutor(max_workers=processes) as executor:
        futures = [
            executor.submit(load_dataset, dataset) for dataset in datasets_sample
        ]
        concurrent.futures.wait(futures)
        # We have to get the result (even though we don't use it) in order to get the exceptions
        for future in futures:
            try:
                future.result()
            except Exception:
                print(traceback.format_exc())

    engine = get_engine()
    with engine.begin() as connection:
        activity_result = connection.execute(
            text("SELECT COUNT(*) AS count FROM _raw_activity")
        ).first()
        logger.info(
            f"Loaded {activity_result.count if activity_result else 0} activities into database"
        )
        organisation_result = connection.execute(
            text("SELECT COUNT(*) AS count FROM _raw_organisation")
        ).first()
        logger.info(
            f"Loaded {organisation_result.count if organisation_result else 0} organisations into database"
        )


def process_registry() -> None:
    raw_objects()
    schema_analysis()
    postgres_tables()
    sql_process()


def flatten_object(obj, current_path="", no_index_path=tuple()):
    for key, value in list(obj.items()):
        new_no_index_path = no_index_path + (key,)

        key = key.replace("-", "")
        key = key.replace("@{http://www.w3.org/XML/1998/namespace}", "")
        key = key.replace("@", "")
        if isinstance(value, dict):
            yield from flatten_object(value, f"{current_path}{key}_", new_no_index_path)
        else:
            if isinstance(value, str):
                codelist_value_name = ALL_CODELIST_LOOKUP.get(
                    (new_no_index_path, value)
                )
                if codelist_value_name:
                    yield f"{current_path}{key}name", codelist_value_name

            if key == "$":
                if current_path:
                    yield f"{current_path}"[:-1], value
                else:
                    yield "_", value
            else:
                yield f"{current_path}{key}", value


@functools.lru_cache(1000)
def path_info(
    full_path: tuple[str | int, ...], no_index_path: tuple[str, ...], filetype: str
) -> tuple[str, list[str], list[str], str, tuple[dict[str, str], ...]]:
    all_paths = []
    for num, part in enumerate(full_path):
        if isinstance(part, int):
            all_paths.append(full_path[: num + 1])

    parent_paths = all_paths[:-1]
    path_key = all_paths[-1] if all_paths else []

    object_key = ".".join(str(key) for key in path_key)
    parent_keys_list = [
        ".".join(str(key) for key in parent_path) for parent_path in parent_paths
    ]
    parent_keys_no_index = [
        "_".join(str(key) for key in parent_path if not isinstance(key, int))
        for parent_path in parent_paths
    ]
    object_type = "_".join(str(key) for key in no_index_path) or filetype
    parent_keys = (dict(zip(parent_keys_no_index, parent_keys_list)),)
    return object_key, parent_keys_list, parent_keys_no_index, object_type, parent_keys


def traverse_object(
    obj: dict[str, Any], emit_object: bool, full_path=tuple(), no_index_path=tuple()
) -> Iterator[tuple[dict[str, Any], tuple[Any, ...], tuple[str, ...]]]:
    for original_key, value in list(obj.items()):
        key = original_key.replace("-", "")

        if key == "narrative":
            narratives = []
            for narrative in value:
                if not narrative:
                    continue
                if isinstance(narrative, dict):
                    lang = (
                        narrative.get("@{http://www.w3.org/XML/1998/namespace}lang", "")
                        or ""
                    )
                    narrative = f"{lang.upper()}: {narrative.get('$', '')}"
                narratives.append(narrative)
            obj["narrative"] = ", ".join(narratives)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for num, item in enumerate(value):
                if not isinstance(item, dict):
                    item = {"__error": "A non object is in array of objects"}
                yield from traverse_object(
                    item, True, full_path + (key, num), no_index_path + (key,)
                )
            obj.pop(original_key)
        elif isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                obj[key] = json.dumps(value)
        elif isinstance(value, dict):
            yield from traverse_object(
                value, False, full_path + (key,), no_index_path + (key,)
            )

    if obj and emit_object:
        new_object = {key.replace("-", ""): value for key, value in obj.items()}
        yield new_object, full_path, no_index_path


DATE_MAP = {
    "1": "plannedstart",
    "2": "actualstart",
    "3": "plannedend",
    "4": "actualend",
}
DATE_MAP_BY_FIELD = {value: int(key) for key, value in DATE_MAP.items()}


def create_rows(
    id: int, dataset: str, prefix: str, original_object: dict[str, Any], filetype: str
) -> Iterator[dict[str, Any]]:
    if original_object is None:
        return []

    # get activity dates before traversal remove them
    activity_dates = original_object.get("activity-date", []) or []

    for object, full_path, no_index_path in traverse_object(original_object, True):
        (
            object_key,
            parent_keys_list,
            parent_keys_no_index,
            object_type,
            parent_keys,
        ) = path_info(full_path, no_index_path, filetype)

        object["_link"] = f'{id}{"." if object_key else ""}{object_key}'
        object["dataset"] = dataset
        object["prefix"] = prefix

        if filetype == "activity":
            object["_link_activity"] = str(id)
            if object_type == "activity":
                for activity_date in activity_dates:
                    if not isinstance(activity_date, dict):
                        continue
                    type = activity_date.get("@type")
                    date = activity_date.get("@iso-date")
                    if type and date and type in DATE_MAP:
                        object[DATE_MAP[type]] = date
            else:
                object["iatiidentifier"] = original_object.get("iati-identifier")
                reporting_org = original_object.get("reporting-org", {}) or {}
                object["reportingorg_ref"] = reporting_org.get("@ref")
        elif filetype == "organisation":
            object["_link_organisation"] = str(id)
            if object_type != "organisation":
                object_type = f"organisation_{object_type}"

        for no_index, full in zip(parent_keys_no_index, parent_keys_list):
            object[f"_link_{no_index}"] = f"{id}.{full}"

        yield dict(
            id=id,
            object_key=object_key,
            parent_keys=json.dumps(parent_keys),
            object_type=object_type,
            object=json.dumps(
                dict(flatten_object(object, no_index_path=no_index_path))
            ),
            filetype=filetype,
        )


def raw_objects() -> None:
    logger.info("Flattening activities and organisations into objects")
    get_codelists_lookup()

    logger.debug("Creating table: _raw_objects")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DROP TABLE IF EXISTS _raw_objects;
                CREATE TABLE _raw_objects(
                    id bigint,
                    object_key TEXT,
                    parent_keys JSONB,
                    object_type TEXT,
                    object JSONB,
                    filetype TEXT
                );
                """
            )
        )

    with engine.begin() as read_connection:
        with engine.begin() as write_connection:
            read_connection = read_connection.execution_options(
                stream_results=True, max_row_buffer=1000
            )
            results = read_connection.execute(
                text(
                    """
                    (SELECT id, dataset, prefix, object, 'activity' AS filetype FROM _raw_activity ORDER BY id)
                    UNION ALL
                    (SELECT id, dataset, prefix, object, 'organisation' AS filetype FROM _raw_organisation ORDER BY id)
                    """
                )
            )

            for num, (id, dataset, prefix, original_object, filetype) in enumerate(
                results
            ):
                if num % 10000 == 0:
                    logger.info(f"Processed {num} objects so far")
                write_connection.execute(
                    insert(
                        table(
                            "_raw_objects",
                            column("id"),
                            column("object_key"),
                            column("parent_keys"),
                            column("object_type"),
                            column("object"),
                            column("filetype"),
                        )
                    ).values(
                        [
                            {
                                "id": row["id"],
                                "object_key": row["object_key"],
                                "parent_keys": row["parent_keys"],
                                "object_type": row["object_type"],
                                "object": row["object"],
                                "filetype": row["filetype"],
                            }
                            for row in create_rows(
                                id, dataset, prefix, original_object, filetype
                            )
                        ]
                    )
                )


DATE_RE = r"^(\d{4})-(\d{2})-(\d{2})([T ](\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?))?$"


def schema_analysis():
    logger.info("Analysing schema")
    create_table(
        "_object_type_aggregate",
        f"""SELECT
              object_type,
              each.key,
              CASE
                 WHEN jsonb_typeof(value) != 'string'
                     THEN jsonb_typeof(value)
                 WHEN (value ->> 0) ~ '{DATE_RE}'
                     THEN 'datetime'
                 ELSE 'string'
              END value_type,
              count(*)
           FROM
              _raw_objects ro, jsonb_each(object) each
           GROUP BY 1,2,3;
        """,
    )

    create_table(
        "_object_type_fields",
        """SELECT
              object_type,
              key,
              CASE WHEN
                  count(*) > 1
              THEN 'string'
              ELSE max(value_type) end value_type,
              SUM("count") AS "count"
           FROM
              _object_type_aggregate
           WHERE
              value_type != 'null'
           GROUP BY 1,2;
        """,
    )

    schema_lookup = get_schema_docs()

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                drop table if exists _fields;
                create table _fields (table_name TEXT, field TEXT, type TEXT, count INT, docs TEXT, field_order INT)
                """
            )
        )

        results = connection.execute(
            text("SELECT object_type, key, value_type, count FROM _object_type_fields")
        )

        for object_type, key, value_type, count in results:
            order, docs = 9999, ""

            if object_type == "activity":
                path = key
            else:
                path = object_type + "_" + key
            if key.startswith("_link"):
                order = 0
                if key == "_link":
                    docs = (
                        "Primary Key for this table. "
                        "It is unique and used for other tables rows to join to this table."
                    )
                else:
                    docs = f"Foreign key to {key[6:]} tables `_link` field"
            elif key == "dataset":
                order, docs = 0, "The name of the dataset this row came from."
            elif key == "prefix":
                order, docs = 0, ""
            elif key == "iatiidentifier":
                order, docs = 1, "A globally unique identifier for the activity."
            elif key == "reportingorg_ref" and object_type != "activity":
                order, docs = (
                    2,
                    "Machine-readable identification string for the organisation issuing the report.",
                )
            elif key in DATE_MAP_BY_FIELD:
                order, docs = DATE_MAP_BY_FIELD[key] + 2, key
            else:
                order, docs = schema_lookup.get(path, [9999, ""])
                if not docs:
                    if key.endswith("name"):
                        order, docs = schema_lookup.get(path[:-4], [9999, ""])

            fields_table = table(
                "_fields",
                column("table_name"),
                column("field"),
                column("type"),
                column("count"),
                column("docs"),
                column("field_order"),
            )

            connection.execute(
                insert(fields_table).values(
                    {
                        "table_name": object_type,
                        "field": key,
                        "type": value_type,
                        "count": count,
                        "docs": docs,
                        "field_order": order,
                    },
                )
            )

        connection.execute(
            text(
                """
                INSERT INTO _fields VALUES (
                    'metadata', 'data_dump_updated_at', 'datetime', 1, 'Time of IATI data dump', 9999
                );
                INSERT INTO _fields VALUES (
                    'metadata', 'iati_tables_updated_at', 'datetime', 1, 'Time of IATI tables processing', 9999
                );
                """
            )
        )

    create_table(
        "_tables",
        """
        SELECT table_name, min(field_order) table_order, max("count") as rows
        FROM _fields WHERE field_order > 10 GROUP BY table_name
        """,
    )


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


def get_data_dump_updated_at() -> datetime:
    with open(f"{pathlib.Path()}/__iatikitcache__/registry/metadata.json") as f:
        metadata = json.load(f)
        return datetime.strptime(metadata.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ")


def postgres_tables(drop_release_objects=False):
    logger.info("Creating postgres tables")
    object_details = defaultdict(list)
    with get_engine().begin() as connection:
        result = list(
            connection.execute(
                text(
                    """
                    SELECT table_name, field, type
                    FROM _fields
                    ORDER BY table_name, field_order, field
                    """
                )
            )
        )
        for row in result:
            object_details[row.table_name].append(dict(name=row.field, type=row.type))

    for object_type, object_detail in object_details.items():
        field_sql, as_sql = create_field_sql(object_detail)
        table_sql = f"""
            SELECT {field_sql}
            FROM _raw_objects, jsonb_to_record(object) AS x({as_sql})
            WHERE object_type = :object_type
            """
        create_table(object_type, table_sql, object_type=object_type)

    logger.debug("Creating table: metadata")
    with get_engine().begin() as connection:
        connection.execute(
            text(
                """
                DROP TABLE IF EXISTS metadata;
                CREATE TABLE metadata(data_dump_updated_at timestamp, iati_tables_updated_at timestamp);
                INSERT INTO metadata values(:data_dump_updated_at, :iati_tables_updated_at);
                """
            ),
            {
                "data_dump_updated_at": get_data_dump_updated_at().isoformat(
                    sep=" ", timespec="seconds"
                ),
                "iati_tables_updated_at": datetime.utcnow().isoformat(
                    sep=" ", timespec="seconds"
                ),
            },
        )

    if drop_release_objects:
        with get_engine().begin() as connection:
            connection.execute("DROP TABLE IF EXISTS _release_objects")

    engine = get_engine()
    with engine.begin() as connection:
        tables = connection.execute(
            text(
                "SELECT table_name, rows FROM _tables ORDER BY table_order, table_name"
            )
        )
        for table_name, rows in tables:
            logger.info(f"There are {rows} rows in {table_name}")


def augment_transaction():
    logger.debug("Augmenting transaction table")
    with get_engine().begin() as connection:
        connection.execute(
            text(
                """
                drop table if exists _exchange_rates;
                create table _exchange_rates(
                    date text, rate float, Currency text, frequency text, source text, country_code text, country text
                );
                """
            )
        )

        r = requests.get(
            "https://raw.githubusercontent.com/codeforIATI/imf-exchangerates/gh-pages/imf_exchangerates.csv",
            stream=True,
        )
        f = StringIO(r.text)
        dbapi_conn = connection.connection
        copy_sql = "COPY _exchange_rates FROM STDIN WITH (FORMAT CSV, HEADER)"
        cur = dbapi_conn.cursor()
        cur.copy_expert(copy_sql, f)

        connection.execute(
            text(
                """
                drop table if exists _monthly_currency;
                create table _monthly_currency as
                    select distinct on (substring(date, 1,7), currency) substring(date, 1,7) yearmonth, rate, currency
                    from _exchange_rates;
                """
            )
        )

        _create_table(
            "tmp_transaction_usd",
            connection,
            """
            select
                t._link,
                case
                    when coalesce(value_currency, activity.defaultcurrency) = 'USD' then value
                    when rate = 0 then null
                    else value / rate
                end value_usd
            from
                transaction t
            join
                activity using (_link_activity)
            left join _monthly_currency mc
                on greatest(substring(value_valuedate::text, 1,7), to_char(current_date-60, 'yyyy-mm')) = yearmonth
                and lower(coalesce(value_currency, activity.defaultcurrency)) =  lower(currency)
           """,
        )

        _create_table(
            "tmp_transaction_sector",
            connection,
            """
            select distinct on (_link_transaction) _link_transaction, code, codename
            from transaction_sector
            where vocabulary is null or vocabulary in ('', '1');
            """,
        )

        _create_table(
            "tmp_transaction",
            connection,
            """SELECT
                   t.*, value_usd, ts.code as sector_code, ts.codename as sector_codename
               FROM
                   transaction t
               LEFT JOIN
                    tmp_transaction_sector ts on t._link = ts._link_transaction
               LEFT JOIN
                    tmp_transaction_usd usd on t._link = usd._link
            """,
        )

        sum_value_usd, sum_sector_code, sum_sector_codename = connection.execute(
            text(
                """
                select
                    sum(case when value_usd is not null then 1 else 0 end) value_usd,
                    sum(case when sector_code is not null then 1 else 0 end) sector_code,
                    sum(case when sector_codename is not null then 1 else 0 end) sector_codename
                from
                    tmp_transaction
                """
            )
        ).fetchone()

        connection.execute(
            text(
                """
                insert into _fields values(
                    'transaction', 'value_usd', 'number', :sum_value_usd, 'Value in USD', 10000
                );
                insert into _fields values(
                    'transaction',
                    'sector_code',
                    'string',
                    :sum_sector_code,
                    'Sector code for default vocabulary',
                    10001
                );
                insert into _fields values(
                    'transaction',
                    'sector_codename',
                    'string',
                    :sum_sector_codename,
                    'Sector code name for default vocabulary',
                    10002
                );
                """
            ),
            {
                "sum_value_usd": sum_value_usd,
                "sum_sector_code": sum_sector_code,
                "sum_sector_codename": sum_sector_codename,
            },
        )

        connection.execute(
            text(
                """
                drop table if exists tmp_transaction_usd;
                drop table if exists tmp_transaction_sector;
                drop table if exists transaction;
                alter table tmp_transaction rename to transaction;
                """
            )
        )


def transaction_breakdown():
    logger.debug("Creating transaction_breakdown table")
    with get_engine().begin() as connection:
        connection.execute(
            text(
                """
                drop table if exists transaction_breakdown;
                create table transaction_breakdown AS

                with sector_count AS (
                    select
                        _link_activity,
                        code,
                        codename,
                        coalesce(percentage, 100) as percentage,
                        count(*) over activity AS cou,
                        sum(coalesce(percentage, 100)) over activity AS total_percentage
                    FROM sector
                    where coalesce(vocabulary, '1') = '1'
                    and coalesce(percentage, 100) <> 0 window activity as (partition by _link_activity)),

                country_100 AS (
                    SELECT _link_activity from recipientcountry group by 1 having sum(coalesce(percentage, 100)) >= 100
                ),

                country_region AS (
                    select *, sum(percentage) over (partition by _link_activity) AS total_percentage from
                        (
                            select
                                prefix,
                                _link_activity,
                                'country' as locationtype,
                                code as country_code,
                                codename as country_codename,
                                '' as region_code ,
                                '' as region_codename,
                                coalesce(percentage, 100) as percentage
                            FROM recipientcountry where coalesce(percentage, 100) <> 0

                            union all

                            select
                                rr.prefix,
                                _link_activity,
                                'region' as locationtype,
                                '',
                                '',
                                code as regioncode,
                                codename,
                                coalesce(percentage, 100) as percentage
                            FROM recipientregion rr
                            LEFT JOIN country_100 c1 using (_link_activity)
                            WHERE coalesce(vocabulary, '1') = '1'
                            and coalesce(percentage, 100) <> 0
                            and c1._link_activity is null
                        ) a
                )

                select
                    t.prefix,
                    t._link_activity,
                    t._link as _link_transaction,
                    t.iatiidentifier,
                    t.reportingorg_ref,
                    t.transactiontype_code,
                    t.transactiontype_codename,
                    t.transactiondate_isodate,
                    coalesce(t.sector_code, sc.code) sector_code,
                    coalesce(t.sector_codename, sc.codename) sector_codename,
                    coalesce(t.recipientcountry_code, cr.country_code) recipientcountry_code,
                    coalesce(t.recipientcountry_codename, cr.country_codename) recipientcountry_codename,
                    coalesce(t.recipientregion_code, cr.region_code) recipientregion_code,
                    coalesce(t.recipientregion_codename, cr.region_codename) recipientregion_codename,
                    (
                        value *
                        coalesce(sc.percentage/sc.total_percentage, 1) *
                        coalesce(cr.percentage/cr.total_percentage, 1)
                    ) AS value,
                    t.value_currency,
                    t.value_valuedate,
                    (
                        value_usd *
                        coalesce(sc.percentage/sc.total_percentage, 1) *
                        coalesce(cr.percentage/cr.total_percentage, 1)
                    ) AS value_usd,
                    (
                        coalesce(sc.percentage/sc.total_percentage, 1) *
                        coalesce(cr.percentage/cr.total_percentage, 1)
                    ) AS percentage_used
                from
                transaction t
                left join
                sector_count sc on t._link_activity = sc._link_activity and t.sector_code is null
                left join country_region cr
                    on t._link_activity = cr._link_activity
                    and coalesce(t.recipientregion_code, t.recipientcountry_code) is null
                    and cr.total_percentage<>0;

                insert into _tables
                    select
                        'transaction_breakdown',
                        (
                            select max(case when table_order = 9999 then 0 else table_order end)
                            from _tables
                        ) count,
                        (
                            select count(*)
                            from transaction_breakdown
                        );
                """
            )
        )

        result = connection.execute(
            text(
                """
                select
                    sum(case when prefix is not null then 1 else 0 end) prefix,
                    sum(case when _link_activity is not null then 1 else 0 end) _link_activity,
                    sum(case when _link_transaction is not null then 1 else 0 end) _link_transaction,
                    sum(case when iatiidentifier is not null then 1 else 0 end) iatiidentifier,
                    sum(case when reportingorg_ref is not null then 1 else 0 end) reportingorg_ref,
                    sum(case when transactiontype_code is not null then 1 else 0 end) transactiontype_code,
                    sum(case when transactiontype_codename is not null then 1 else 0 end) transactiontype_codename,
                    sum(case when transactiondate_isodate is not null then 1 else 0 end) transactiondate_isodate,
                    sum(case when sector_code is not null then 1 else 0 end) sector_code,
                    sum(case when sector_codename is not null then 1 else 0 end) sector_codename,
                    sum(case when recipientcountry_code is not null then 1 else 0 end) recipientcountry_code,
                    sum(case when recipientcountry_codename is not null then 1 else 0 end) recipientcountry_codename,
                    sum(case when recipientregion_code is not null then 1 else 0 end) recipientregion_code,
                    sum(case when recipientregion_codename is not null then 1 else 0 end) recipientregion_codename,
                    sum(case when value is not null then 1 else 0 end) "value",
                    sum(case when value_currency is not null then 1 else 0 end) value_currency,
                    sum(case when value_valuedate is not null then 1 else 0 end) value_valuedate,
                    sum(case when value_usd is not null then 1 else 0 end) value_usd,
                    sum(case when percentage_used is not null then 1 else 0 end) percentage_used
                from
                    transaction_breakdown
                """
            )
        ).fetchone()

        connection.execute(
            text(
                """
                insert into _fields values ('transaction_breakdown','prefix','string',:prefix,'', -1);
                insert into _fields values (
                    'transaction_breakdown','_link_activity','string',:_link_activity,'_link field', 1
                );
                insert into _fields values (
                    'transaction_breakdown','_link_transaction','string',:_link_transaction,'_link field', 2
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'iatiidentifier',
                    'string',
                    :iatiidentifier,
                    'A globally unique identifier for the activity.',
                    3
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'reportingorg_ref',
                    'string',
                    :reportingorg_ref,
                    'Machine-readable identification string for the organisation issuing the report.',
                    4
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'transactiontype_code',
                    'string',
                    :transactiontype_code,
                    'Transaction Type Code',
                    5
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'transactiontype_codename',
                    'string',
                    :transactiontype_codename,
                    'Transaction Type Codelist Name',
                    6
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'transactiondate_isodate',
                    'string',
                    :transactiondate_isodate,
                    'Transaction date',
                    7
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'sector_code',
                    'string',
                    :sector_code,
                    'Sector code',
                    8
                );
                insert into _fields values (
                    'transaction_breakdown','sector_codename','string',:sector_codename,'Sector code codelist name', 9
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'recipientcountry_code',
                    'string',
                    :recipientcountry_code,
                    'Recipient Country Code',
                    10
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'recipientcountry_codename',
                    'string',
                    :recipientcountry_codename,
                    'Recipient Country Code',
                    11
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'recipientregion_code',
                    'string',
                    :recipientregion_code,
                    'Recipient Region Code',
                    12
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'recipientregion_codename',
                    'string',
                    :recipientregion_codename,
                    'Recipient Region Codelist Name',
                    13
                );
                insert into _fields values ('transaction_breakdown','value','number',:value,'Value', 14);
                insert into _fields values (
                    'transaction_breakdown','value_currency','string',:value_currency,'Transaction Currency', 15
                );
                insert into _fields values (
                    'transaction_breakdown','value_valuedate','datetime',:value_valuedate,'Transaction Date', 16
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'value_usd',
                    'number',
                    :value_usd,
                    'Value in USD',
                    17
                );
                insert into _fields values (
                    'transaction_breakdown',
                    'percentage_used',
                    'number',
                    :percentage_used,
                    'Percentage of transaction this row represents',
                    18
                );
                """
            ),
            {
                "prefix": result.prefix,
                "_link_activity": result._link_activity,
                "_link_transaction": result._link_transaction,
                "iatiidentifier": result.iatiidentifier,
                "reportingorg_ref": result.reportingorg_ref,
                "transactiontype_code": result.transactiontype_code,
                "transactiontype_codename": result.transactiontype_codename,
                "transactiondate_isodate": result.transactiondate_isodate,
                "sector_code": result.sector_code,
                "sector_codename": result.sector_codename,
                "recipientcountry_code": result.recipientcountry_code,
                "recipientcountry_codename": result.recipientcountry_codename,
                "recipientregion_code": result.recipientregion_code,
                "recipientregion_codename": result.recipientregion_codename,
                "value": result.value,
                "value_currency": result.value_currency,
                "value_valuedate": result.value_valuedate,
                "value_usd": result.value_usd,
                "percentage_used": result.percentage_used,
            },
        )


def sql_process():
    try:
        augment_transaction()
        transaction_breakdown()
    except Exception:
        logger.error(
            "Processing on the 'transaction' table failed, this is usually caused by the sample size being too small"
        )
        raise


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


def export_all():
    export_stats()
    export_sqlite()
    export_csv()
    export_pgdump()
    try:
        export_bigquery()
    except Exception:
        logger.warning("Big query failed, proceeding anyway")


def upload_all():
    if s3_destination and s3_destination != "-":
        logger.info("Uploading files to S3")
        files = [
            "stats.json",
            "iati.sqlite.gz",
            "iati.db.gz",
            "iati.sqlite",
            "iati.sqlite.zip",
            "activities.json.gz",
            "iati_csv.zip",
            "iati.custom.pg_dump",
            "iati.dump.gz",
        ]
        for file in files:
            subprocess.run(
                ["s3cmd", "put", f"{output_dir}/{file}", s3_destination], check=True
            )
            subprocess.run(
                ["s3cmd", "setacl", f"{s3_destination}{file}", "--acl-public"],
                check=True,
            )
    else:
        logger.info("Skipping upload to S3")


def run_all(
    sample: Optional[int] = None, refresh: bool = True, processes: int = 5
) -> None:
    extract(refresh=refresh)
    load(processes=processes, sample=sample)
    process_registry()
    export_all()
    upload_all()
