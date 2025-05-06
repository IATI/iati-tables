import functools
import json
import logging
import pathlib
from collections import defaultdict
from datetime import datetime
from io import StringIO
from typing import Any, Iterator

import iatikit
import requests
from sqlalchemy import column, insert, table, text

from iati_tables.database import (
    _create_table,
    create_field_sql,
    create_table,
    get_engine,
)
from iati_tables.load import IATISchemaWalker

logger = logging.getLogger(__name__)


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


def traverse_object(
    obj: dict[str, Any], emit_object: bool, full_path=tuple(), no_index_path=tuple()
) -> Iterator[tuple[dict[str, Any], tuple[Any, ...], tuple[str, ...]]]:
    for original_key, value in list(obj.items()):
        key = original_key.replace("-", "")

        if key == "narrative":
            # Old narrative format, kept for backwards compatibility reasons
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
            # But also keep processing, so we get nice narrative tables too.
            # https://github.com/IATI/iati-tables/issues/79
            if isinstance(value, list):
                for num, item in enumerate(value):
                    # In this case there could be mixed strings and dicts in this list
                    # (so we aren't just reusing the code below)
                    if isinstance(item, dict):
                        yield from traverse_object(
                            item, True, full_path + (key, num), no_index_path + (key,)
                        )
                    elif isinstance(item, str):
                        yield {"$": item}, full_path + (key, num), no_index_path + (
                            key,
                        )
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


def flatten_schema_docs(cur, path=""):
    for field, value in cur.items():
        info = value.get("info")
        docs = info.get("docs", "")
        yield f"{path}{field}", docs
        for attribute, attribute_docs in info.get("attributes", {}).items():
            yield f"{path}{field}_{attribute}", attribute_docs

        yield from flatten_schema_docs(value.get("properties", {}), f"{path}{field}_")


def get_schema_docs():
    schema_docs = IATISchemaWalker().create_schema_docs("iati-activity")

    schema_docs_lookup = {}
    for num, (field, doc) in enumerate(flatten_schema_docs(schema_docs)):
        field = field.replace("-", "")
        # leave some space for extra fields at the start
        schema_docs_lookup[field] = [num + 10, doc]

    return schema_docs_lookup


DATE_RE = r"^(\d{4})-(\d{2})-(\d{2})$"
DATETIME_RE = r"^(\d{4})-(\d{2})-(\d{2})([T ](\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?))?$"


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
                     THEN 'date'
                 WHEN (value ->> 0) ~ '{DATETIME_RE}'
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
                "data_dump_updated_at": iatikit.data().last_updated.isoformat(
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


def process_registry() -> None:
    raw_objects()
    schema_analysis()
    postgres_tables()
    sql_process()
