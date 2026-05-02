"""Thin boto3 wrapper for the R2 uploader.

Isolates the S3-compatible client setup and the operations the uploader
needs (head_object existence check, file upload, inventory read/write)
so `r2_upload.py` stays focused on orchestration + validation.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "bsdata-prod"
INVENTORY_KEY = "_inventory.json"


def make_s3_client() -> tuple[Any, str]:
    """Build a boto3 S3 client for Cloudflare R2 + return (client, bucket).

    Reads from env vars:
        BS_R2_BUCKET     (default: bsdata-prod)
        BS_R2_ENDPOINT   (required)
        BS_R2_ACCESS_KEY (required)
        BS_R2_SECRET     (required)

    Raises RuntimeError if required vars are missing.
    """
    import boto3

    bucket = os.environ.get("BS_R2_BUCKET", DEFAULT_BUCKET)
    endpoint = os.environ.get("BS_R2_ENDPOINT")
    access_key = os.environ.get("BS_R2_ACCESS_KEY")
    secret_key = os.environ.get("BS_R2_SECRET")
    if not (endpoint and access_key and secret_key):
        raise RuntimeError(
            "r2_upload requires BS_R2_ENDPOINT, BS_R2_ACCESS_KEY, "
            "and BS_R2_SECRET to be set"
        )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return client, bucket


def object_exists_with_size(client: Any, bucket: str, key: str, expected_size: int) -> bool:
    """True if the R2 object exists and has the expected byte size.

    Used for cheap idempotency: skip upload when local size matches R2.
    Note: bytes-equal-but-different-content slips through this check;
    use `--rebuild` to force re-upload after suspected drift.
    """
    from botocore.exceptions import ClientError

    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise
    return head["ContentLength"] == expected_size


def upload_file(client: Any, bucket: str, local_path: Path, key: str) -> None:
    client.upload_file(str(local_path), bucket, key)


def read_inventory(client: Any, bucket: str) -> dict | None:
    """Fetch and parse `_inventory.json` from R2. Returns None if missing.

    Used as the cheap idempotency cache: with 100K+ partitions, head_object
    per file each run blows past R2's 1M Class A op/month free tier in
    hours. Trusting inventory means one Class B op per run instead.

    The trade-off: if someone uploads to the bucket outside this uploader,
    we won't see those files until next inventory rewrite. For the
    single-uploader BacktestStation setup that's fine; pass `--rebuild`
    to force a full re-upload if you suspect drift.
    """
    from botocore.exceptions import ClientError

    try:
        obj = client.get_object(Bucket=bucket, Key=INVENTORY_KEY)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return json.loads(obj["Body"].read().decode("utf-8"))


def write_inventory(
    client: Any,
    bucket: str,
    *,
    schema_version: str,
    generator_version: str,
    partitions: list[dict],
) -> None:
    """Serialize and PUT the partition catalog as `_inventory.json`."""
    inventory = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "schema_version": schema_version,
        "generator_version": generator_version,
        "partitions": partitions,
    }
    body = json.dumps(inventory, indent=2, sort_keys=True).encode("utf-8")
    client.put_object(
        Bucket=bucket,
        Key=INVENTORY_KEY,
        Body=body,
        ContentType="application/json",
    )
