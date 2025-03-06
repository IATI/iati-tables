import concurrent.futures
import functools
import json
import logging
import pathlib
from itertools import islice
from typing import Any, Iterator, Optional, OrderedDict

import iatikit
import xmlschema
from lxml import etree
from sqlalchemy import column, insert, table, text

from iati_tables import sort_iati
from iati_tables.database import get_engine, schema

logger = logging.getLogger(__name__)


this_dir = pathlib.Path(__file__).parent.resolve()

VERSION_1_TRANSFORMS = {
    "activity": etree.XSLT(etree.parse(str(this_dir / "iati-activities.xsl"))),
    "organisation": etree.XSLT(etree.parse(str(this_dir / "iati-organisations.xsl"))),
}


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


def parse_dataset(
    dataset: iatikit.Dataset,
) -> Iterator[tuple[dict[str, Any], list[xmlschema.XMLSchemaValidationError]]]:
    try:
        dataset_etree = dataset.etree.getroot()
    except Exception:
        logger.debug(f"Error parsing XML for dataset '{dataset.name}'")
        return

    version = dataset_etree.get("version", "1.01")
    if version.startswith("1"):
        logger.debug(f"Transforming v1 {dataset.filetype} file")
        dataset_etree = VERSION_1_TRANSFORMS[dataset.filetype](dataset_etree).getroot()

    parent_element_name = (
        "iati-organisations"
        if dataset.filetype == "organisation"
        else "iati-activities"
    )
    child_element_name = f"iati-{dataset.filetype}"
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


def load_dataset(dataset: iatikit.Dataset) -> None:
    if not dataset.data_path:
        logger.warn(f"Dataset '{dataset}' not found")
        return

    path = pathlib.Path(dataset.data_path)
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


def load(processes: int, sample: Optional[int] = None) -> None:
    create_database_schema()
    create_raw_tables()

    logger.info(
        f"Loading {len(list(islice(iatikit.data().datasets, sample)))} datasets into database"
    )
    datasets_sample = islice(iatikit.data().datasets, sample)

    with concurrent.futures.ProcessPoolExecutor(max_workers=processes) as executor:
        future_to_dataset = {
            executor.submit(load_dataset, dataset): dataset
            for dataset in datasets_sample
        }
        for future in concurrent.futures.as_completed(future_to_dataset):
            # We have to get the result (even though we don't use it) in order to get the exceptions
            try:
                future.result()
            except Exception as e:
                dataset = future_to_dataset[future]
                logger.error(f"Dataset '{dataset.name}' caused error {e}")

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
