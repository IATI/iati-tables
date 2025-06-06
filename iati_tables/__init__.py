import logging
import os
import time
from typing import Optional

from dotenv import find_dotenv, load_dotenv

from iati_tables.export import export_all
from iati_tables.extract import download_registry, download_standard
from iati_tables.load import load_datasets
from iati_tables.modelling import process_registry
from iati_tables.upload import upload_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)


APP_ENV = os.environ.get("APP_ENV", "local")
logger.info(f"Loading {APP_ENV} environment variables")
load_dotenv(find_dotenv(f".env.{APP_ENV}", usecwd=True))


def run_all(
    sample: Optional[int] = None,
    refresh: bool = True,
    refresh_standard: bool = False,
    refresh_registry: bool = False,
    processes: int = 5,
) -> None:
    download_standard(refresh=(refresh_standard or refresh))
    download_registry(refresh=(refresh_registry or refresh))
    load_datasets(processes=processes, sample=sample)
    process_registry()
    export_all()
    upload_all()
