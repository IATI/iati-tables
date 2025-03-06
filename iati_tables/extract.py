import logging
import pathlib

import iatikit

logger = logging.getLogger(__name__)


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
