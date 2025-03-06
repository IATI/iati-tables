import logging
import os
import subprocess

s3_destination = os.environ.get("IATI_TABLES_S3_DESTINATION", "-")
output_dir = os.environ.get("IATI_TABLES_OUTPUT", ".")

logger = logging.getLogger(__name__)


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
