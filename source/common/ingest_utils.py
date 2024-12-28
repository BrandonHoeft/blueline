# source/ingest.py
"""
Shared utility functions for data ingestion flows with prefect
Contains common functionality for MinIO interactions, URL building, data requests for NHL DFS data lake.
"""

import base64
import json
import requests
import datetime
import dateutil.parser as dparser
from minio import Minio
from io import BytesIO
from prefect import task, flow, get_run_logger
from prefect.tasks import task_input_hash
from typing import Dict, Any, List, Optional
import yaml

@task
def load_credentials(creds_path: str = "config/creds.yml") -> Dict[str, Any]:
    """Load API and service credentials from yaml file."""
    with open(creds_path, 'r') as ymlfile:
        return yaml.safe_load(ymlfile)

@task
def init_minio_client(creds: Dict[str, Any]) -> Minio:
    """Initialize MinIO client with credentials."""
    return Minio(
        creds['minio']['endpoint'],
        access_key=creds['minio']['access_key'],
        secret_key=creds['minio']['secret_key'],
        secure=False
    )


@task
def build_msf_url(season: str, date: str, endpoint: str) -> str:
    """
    Build MySportsFeeds API URL

    Parameters:
        season: Format '2023-2024-regular' or '2024-playoff'
        date: Format YYYYMMDD
        endpoint: 'dfs' or 'dfs_projections'
    """
    logger = get_run_logger()
    logger.info(f"Building URL for endpoint: {endpoint}, date: {date}")
    return f"https://api.mysportsfeeds.com/v2.1/pull/nhl/{season}/date/{date}/{endpoint}.json"


@task(retries=3, retry_delay_seconds=60)
def fetch_msf_data(url: str, creds_path: str, params: Optional[Dict] = None) -> \
Dict[str, Any]:
    """Fetch data from MySportsFeeds API with authentication."""
    logger = get_run_logger()

    # Load credentials
    creds = load_credentials(creds_path)
    api_key = creds['msf']['key']
    password = creds['msf']['password']

    headers = {
        "Authorization": "Basic " + base64.b64encode(
            f'{api_key}:{password}'.encode('utf-8')
        ).decode('ascii')
    }

    if params is None:
        params = {'dfstype': 'draftkings'}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    logger.info(f"Successfully fetched data from API with status code {response.status_code}")
    return response.json()


@task
def generate_file_path(provider: str, context: str, dataset_name: str,
                       schema_version: str, date: str) -> str:
    """Generate consistent file paths for data lake storage."""
    return f"{provider}/{context}/{dataset_name}/v={schema_version}/date={date}/{dataset_name}_{date}.json"


@task
def save_to_minio(data: Dict[str, Any], bucket_name: str,
                  object_name: str, minio_client: Minio) -> None:
    """Save data to MinIO data lake."""
    logger = get_run_logger()

    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        logger.info(f"Created new bucket: {bucket_name}")

    raw_data = json.dumps(data).encode('utf-8')
    minio_client.put_object(
        bucket_name,
        object_name,
        BytesIO(raw_data),
        len(raw_data)
    )
    logger.info(f"Successfully saved data to {bucket_name}/{object_name}")

