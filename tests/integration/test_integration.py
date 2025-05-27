import datetime
import json
from decimal import Decimal
from typing import Any
from unittest import mock
from unittest.mock import MagicMock

import pytest
from deepdiff import DeepDiff
from iatikit.data.dataset import Dataset
from sqlalchemy import text

from iati_tables import run_all
from iati_tables.database import get_engine

mock_iatikit_data = MagicMock()
mock_iatikit_data.datasets = {
    Dataset(data_path="tests/fixtures/test_prefix/test_activity.xml"),
    Dataset(data_path="tests/fixtures/test_prefix/test_organisation.xml"),
}
mock_iatikit_data.last_updated = datetime.datetime.now()
mock_iatikit = MagicMock()
mock_iatikit.data.return_value = mock_iatikit_data


@pytest.fixture(scope="module", autouse=True)
@mock.patch("iati_tables.load.iatikit", mock_iatikit)
@mock.patch("iati_tables.modelling.iatikit", mock_iatikit)
@mock.patch("iati_tables.download_registry", MagicMock())
def run_pipeline() -> None:
    run_all(refresh=False)


def assert_table_contents(table_name: str, expected_rows: list[dict[str, Any]]) -> None:
    with get_engine().begin() as connection:
        result = connection.execute(text(f"SELECT * FROM {table_name}"))
        actual = [dict(row) for row in result.mappings().all()]
        expected_count = len(expected_rows)
        assert (
            len(actual) == expected_count
        ), f"Expected there to be {expected_count} rows in {table_name} table"
        diff = DeepDiff(actual, expected_rows, ignore_order=True)
        assert (
            diff == {}
        ), f"Differences between expected and actual:\n{json.dumps(diff, default=str, indent=4)}"


def test_activity() -> None:
    assert_table_contents(
        "activity",
        expected_rows=[
            {
                "_link": "1",
                "_link_activity": "1",
                "dataset": "test_activity",
                "prefix": "test_prefix",
                "lastupdateddatetime": datetime.datetime(2014, 9, 10, 7, 15, 37),
                "lang": "en",
                "defaultcurrency": "USD",
                "defaultcurrencyname": "US Dollar",
                "humanitarian": True,
                "hierarchy": Decimal(1),
                "linkeddatauri": "http://data.example.org/123456789",
                "budgetnotprovided": "1",
                "budgetnotprovidedname": "Commercial Restrictions",
                "iatiidentifier": "AA-AAA-123456789-ABC123",
                "reportingorg_ref": "AA-AAA-123456789",
                "reportingorg_type": "40",
                "reportingorg_typename": "Multilateral",
                "reportingorg_secondaryreporter": False,
                "reportingorg_narrative": "Organisation name, FR: Nom de l'organisme",
                "title_narrative": "Activity title, FR: Titre de l'activit\u00e9, ES: T\u00edtulo de la actividad",
                "activitystatus_code": "2",
                "activitystatus_codename": "Implementation",
                "plannedstart": datetime.date(2012, 4, 15),
                "actualstart": datetime.date(2012, 4, 28),
                "plannedend": datetime.date(2015, 12, 31),
                "activityscope_code": "3",
                "activityscope_codename": "Multi-national",
                "countrybudgetitems_vocabulary": "4",
                "countrybudgetitems_vocabularyname": "Reporting Organisation",
                "collaborationtype_code": "1",
                "collaborationtype_codename": "Bilateral",
                "defaultflowtype_code": "10",
                "defaultflowtype_codename": "ODA",
                "defaultfinancetype_code": "110",
                "defaultfinancetype_codename": "Standard grant",
                "defaulttiedstatus_code": "3",
                "defaulttiedstatus_codename": "Partially tied",
                "capitalspend_percentage": Decimal(88.8).__round__(2),
                "conditions_attached": True,
                "crsadd_loanterms_rate1": Decimal(4.0),
                "crsadd_loanterms_rate2": Decimal(3.0),
                "crsadd_loanterms_repaymenttype_code": "1",
                "crsadd_loanterms_repaymentplan_code": "4",
                "crsadd_loanterms_commitmentdate_isodate": datetime.date(2013, 9, 1),
                "crsadd_loanterms_repaymentfirstdate_isodate": datetime.date(
                    2014, 1, 1
                ),
                "crsadd_loanterms_repaymentfinaldate_isodate": datetime.date(
                    2020, 12, 31
                ),
                "crsadd_loanstatus_year": Decimal(2014.0),
                "crsadd_loanstatus_currency": "GBP",
                "crsadd_loanstatus_valuedate": datetime.date(2013, 5, 24),
                "crsadd_loanstatus_interestreceived": Decimal(200000.0),
                "crsadd_loanstatus_principaloutstanding": Decimal(1500000.0),
                "crsadd_loanstatus_principalarrears": Decimal(0.0),
                "crsadd_loanstatus_interestarrears": Decimal(0.0),
                "crsadd_channelcode": "21039",
                "fss_extractiondate": datetime.date(2014, 5, 6),
                "fss_priority": True,
                "fss_phaseoutyear": Decimal(2016.0),
            },
        ],
    )


def test_description():
    assert_table_contents(
        "description",
        expected_rows=[
            {
                "_link": "1.description.0",
                "_link_activity": "1",
                "dataset": "test_activity",
                "prefix": "test_prefix",
                "iatiidentifier": "AA-AAA-123456789-ABC123",
                "reportingorg_ref": "AA-AAA-123456789",
                "type": "1",
                "typename": "General",
                "narrative": "General activity description text. Long description of the activity with no\n        particular structure., FR: Activit\u00e9 g\u00e9n\u00e9rale du texte de description. Longue description de\n        l'activit\u00e9 sans structure particuli\u00e8re.",  # noqa: E501
            },
            {
                "_link": "1.description.1",
                "_link_activity": "1",
                "dataset": "test_activity",
                "prefix": "test_prefix",
                "iatiidentifier": "AA-AAA-123456789-ABC123",
                "reportingorg_ref": "AA-AAA-123456789",
                "type": "2",
                "typename": "Objectives",
                "narrative": "Objectives for the activity, for example from a logical framework., FR: Objectifs de l'activit\u00e9, par exemple \u00e0 partir d'un cadre logique.",  # noqa: E501
            },
            {
                "_link": "1.description.2",
                "_link_activity": "1",
                "dataset": "test_activity",
                "prefix": "test_prefix",
                "iatiidentifier": "AA-AAA-123456789-ABC123",
                "reportingorg_ref": "AA-AAA-123456789",
                "type": "3",
                "typename": "Target Groups",
                "narrative": "Statement of groups targeted to benefit from the activity., FR: D\u00e9claration de groupes cibl\u00e9s pour b\u00e9n\u00e9ficier de l'activit\u00e9.",  # noqa: E501
            },
        ],
    )
