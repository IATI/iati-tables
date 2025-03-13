import datetime
from unittest.mock import MagicMock

from iatikit.data.dataset import Dataset
from pytest_mock import MockerFixture

from iati_tables import run_all


def test_pipeline_runs_successfully(mocker: MockerFixture):
    # Make extract step a no-op
    mocker.patch("iati_tables.download_registry")

    # Set up mock iatikit data
    mock_iatikit_data = MagicMock()
    mock_iatikit_data.datasets = {
        Dataset(data_path="tests/fixtures/test_prefix/test_activity.xml"),
        Dataset(data_path="tests/fixtures/test_prefix/test_organisation.xml"),
    }
    mock_iatikit_data.last_updated = datetime.datetime.now()

    # Make load step use mock iatikit data
    patch_iatikit = mocker.patch("iati_tables.load.iatikit")
    patch_iatikit.data.return_value = mock_iatikit_data

    # Make modelling step use mock iatikit data
    patch_iatikit = mocker.patch("iati_tables.modelling.iatikit")
    patch_iatikit.data.return_value = mock_iatikit_data

    run_all()
