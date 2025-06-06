import logging
import pathlib

import iatikit

logger = logging.getLogger(__name__)


def download_standard(refresh=False):
    if (
        not (pathlib.Path() / "__iatikitcache__").is_dir()
        or not (pathlib.Path() / "__iatikitcache__" / "standard").is_dir()
        or refresh
    ):
        logger.info("Downloading standard")
        iatikit.download.standard()
    else:
        logger.info("Not refreshing standard")


def download_registry(refresh=False):
    if (
        not (pathlib.Path() / "__iatikitcache__").is_dir()
        or not (pathlib.Path() / "__iatikitcache__" / "registry").is_dir()
        or refresh
    ):
        logger.info("Downloading registry data")
        iatikit.download.data()
    else:
        logger.info("Not refreshing registry data")
