"""
Lambda handler — daily entry point for the lunch-bell pipeline.

Flow per school level:
  1. Discover the current month's PDF URL via BeautifulSoup.
  2. Compare the PDF filename against the last-processed value in SSM.
  3. Skip if unchanged (cheap daily run).
  4. Download, parse, generate .ics, upload to S3.
  5. After processing all levels, invalidate the CloudFront cache once.
  6. Update SSM with the new filenames.
"""

import logging
import os
import tempfile
from urllib.parse import urlparse

import boto3
import requests

from discover import discover_lunch_pdfs
from generate import build_calendar
from parse import parse_menu

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ["S3_BUCKET"]
CF_DIST_ID = os.environ["CLOUDFRONT_DIST_ID"]
SSM_PREFIX = os.environ["SSM_PREFIX"]
MENU_PAGE_URL = os.environ.get("MENU_PAGE_URL", "https://www.madisoncity.k12.al.us/Page/3656")
ICAL_DOMAIN = os.environ.get("ICAL_DOMAIN", "curtlawson.dev")

s3 = boto3.client("s3")
ssm = boto3.client("ssm")
cf = boto3.client("cloudfront")


def _get_last_filename(level: str) -> str:
    try:
        resp = ssm.get_parameter(Name=f"{SSM_PREFIX}/{level}")
        return resp["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        return "none"


def _put_last_filename(level: str, filename: str) -> None:
    ssm.put_parameter(
        Name=f"{SSM_PREFIX}/{level}",
        Value=filename,
        Type="String",
        Overwrite=True,
    )


def _pdf_filename(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1]


def lambda_handler(event, context):
    logger.info("Starting lunch-bell run")

    pdfs = discover_lunch_pdfs(page_url=MENU_PAGE_URL)
    logger.info("Discovered PDFs: %s", pdfs)

    changed_levels = []

    for level, url in sorted(pdfs.items()):
        filename = _pdf_filename(url)
        last = _get_last_filename(level)

        if filename == last:
            logger.info("%s: no change (%s), skipping", level, filename)
            continue

        logger.info("%s: new PDF detected (%s), processing", level, filename)

        r = requests.get(url, timeout=30)
        r.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(r.content)
            tmp_path = tmp.name

        menu = parse_menu(tmp_path)
        logger.info("%s: parsed %d lunch days", level, len(menu))

        cal = build_calendar(menu, level, domain=ICAL_DOMAIN)
        ics_bytes = cal.to_ical()

        s3_key = f"{level}.ics"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=ics_bytes,
            ContentType="text/calendar; charset=utf-8",
        )
        logger.info("%s: uploaded s3://%s/%s", level, S3_BUCKET, s3_key)

        changed_levels.append((level, filename))

    if changed_levels:
        cf.create_invalidation(
            DistributionId=CF_DIST_ID,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": str(hash(tuple(changed_levels))),
            },
        )
        logger.info("CloudFront invalidation created for %s", [l for l, _ in changed_levels])

        for level, filename in changed_levels:
            _put_last_filename(level, filename)

    logger.info("Done. Levels updated: %s", [l for l, _ in changed_levels] or "none")
    return {"updated": [l for l, _ in changed_levels]}
