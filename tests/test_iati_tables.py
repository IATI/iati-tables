from collections import OrderedDict

from lxml import etree

from iati_tables import path_info, sort_iati_element, traverse_object


def test_sort_iati_element():
    input_xml = (
        "<iati-activity>"
        "<iati-identifier>XXXXXXXX</iati-identifier>"
        '<activity-status code="2"/>'
        '<transaction><transaction-date iso-date="2024-01-25"/><transaction-type code="3"/></transaction>'
        '<title><narrative xml:lang="en">XXXXXXXX</narrative></title>'
        "</iati-activity>"
    )
    element = etree.fromstring(input_xml)
    schema_dict = OrderedDict(
        [
            ("iati-identifier", OrderedDict()),
            ("title", OrderedDict([("narrative", OrderedDict())])),
            ("activity-status", OrderedDict()),
            (
                "transaction",
                OrderedDict(
                    [
                        ("transaction-type", OrderedDict()),
                        ("transaction-date", OrderedDict()),
                    ]
                ),
            ),
        ]
    )

    sort_iati_element(element, schema_dict)

    expected_xml = (
        b"<iati-activity>"
        b"<iati-identifier>XXXXXXXX</iati-identifier>"
        b'<title><narrative xml:lang="en">XXXXXXXX</narrative></title>'
        b'<activity-status code="2"/>'
        b'<transaction><transaction-type code="3"/><transaction-date iso-date="2024-01-25"/></transaction>'
        b"</iati-activity>"
    )
    assert etree.tostring(element) == expected_xml


def test_traverse_object_strings():
    activity_object = {
        "iati-identifier": "AA-BBB-000000000-CCCC",
    }
    result = list(traverse_object(activity_object, True))
    expected_result = [
        (
            {
                "iatiidentifier": "AA-BBB-000000000-CCCC",
            },
            (),
            (),
        ),
    ]
    assert result == expected_result


def test_traverse_object_dicts():
    activity_object = {
        "activity-status": {"@code": "2"},
    }
    result = list(traverse_object(activity_object, True))
    expected_result = [
        (
            {
                "activitystatus": {"@code": "2"},
            },
            (),
            (),
        ),
    ]
    assert result == expected_result


def test_traverse_object_narratives_plain():
    activity_object = {
        "title": {"narrative": ["Title narrative"]},
    }
    result = list(traverse_object(activity_object, True))
    expected_result = [
        (
            {
                "title": {"narrative": "Title narrative"},
            },
            (),
            (),
        ),
    ]
    assert result == expected_result


def test_traverse_object_narratives_with_language():
    activity_object = {
        "title": {
            "narrative": [
                {
                    "$": "Title narrative",
                    "@{http://www.w3.org/XML/1998/namespace}lang": "en",
                }
            ]
        },
    }
    result = list(traverse_object(activity_object, True))
    expected_result = [
        (
            {
                "title": {"narrative": "EN: Title narrative"},
            },
            (),
            (),
        ),
    ]
    assert result == expected_result


def test_traverse_object_lists_of_dicts():
    activity_object = {
        "transaction": [
            {
                "value": {
                    "$": 2000000.0,
                    "@currency": "GBP",
                    "@value-date": "2024-01-30",
                },
                "description": {"narrative": ["Transaction 0 description narrative"]},
            },
            {
                "value": {
                    "$": 600000.0,
                    "@currency": "USD",
                    "@value-date": "2024-01-31",
                },
                "description": {"narrative": ["Transaction 1 description narrative"]},
            },
        ]
    }
    result = list(traverse_object(activity_object, True))
    expected_result = [
        (
            {
                "value": {
                    "$": 2000000.0,
                    "@currency": "GBP",
                    "@value-date": "2024-01-30",
                },
                "description": {"narrative": "Transaction 0 description narrative"},
            },
            ("transaction", 0),
            ("transaction",),
        ),
        (
            {
                "value": {
                    "$": 600000.0,
                    "@currency": "USD",
                    "@value-date": "2024-01-31",
                },
                "description": {"narrative": "Transaction 1 description narrative"},
            },
            ("transaction", 1),
            ("transaction",),
        ),
    ]
    assert result == expected_result


def test_path_info():
    full_path = ("result", 12, "indicator", 3, "period", 0, "actual", 0)
    no_index_path = ("result", "indicator", "period", "actual")
    (
        object_key,
        parent_keys_list,
        parent_keys_no_index,
        object_type,
        parent_keys,
    ) = path_info(full_path, no_index_path, "activity")

    assert object_key == "result.12.indicator.3.period.0.actual.0"
    assert parent_keys_list == [
        "result.12",
        "result.12.indicator.3",
        "result.12.indicator.3.period.0",
    ]
    assert parent_keys_no_index == [
        "result",
        "result_indicator",
        "result_indicator_period",
    ]
    assert object_type == "result_indicator_period_actual"
    assert parent_keys == (
        {
            "result": "result.12",
            "result_indicator": "result.12.indicator.3",
            "result_indicator_period": "result.12.indicator.3.period.0",
        },
    )
