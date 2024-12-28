# source/ingest.py
"""
Data ingestion script defining the prefect flow logic for NHL DFS data lake.
Handles ingestion from MySportsFeeds API endpoints:
- Daily DFS data (slates, contests, players, salaries)
- DFS Projections data
- Moneypuck.com Team aggregated stats daily

Can be run directly or deployed via Prefect server.
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
from pathlib import Path


def load_credentials(creds_path: str = "config/creds.yml") -> Dict[str, Any]:
    """Load API and service credentials from yaml file."""
    with open(creds_path, 'r') as ymlfile:
        return yaml.safe_load(ymlfile)


def init_minio_client(creds: Dict[str, Any]) -> Minio:
    """Initialize MinIO client with credentials."""
    return Minio(
        creds['minio']['endpoint'],
        access_key=creds['minio']['access_key'],
        secret_key=creds['minio']['secret_key'],
        secure=False
    )


@task(cache_key_fn=task_input_hash)
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

########################## MySportsFeeds APIs ##################################
@flow(name="ingest-dfs-data")
def ingest_dfs_flow(
        date: str = None,
        season: str = "2024-2025-regular",
        endpoint: str = "dfs",
        creds_path: str = "creds.yml"
) -> None:
    """Prefect Flow for ingesting MySportsFeeds Daily DFS data."""
    logger = get_run_logger()

    # Set defaults if not provided
    date = date or datetime.datetime.today().strftime('%Y%m%d')

    # Initialize clients
    creds = load_credentials(creds_path)
    minio_client = init_minio_client(creds)

    # Execute flow
    url = build_msf_url(season, date, endpoint)
    data = fetch_msf_data(url, creds_path)
    parsed_date = dparser.parse(date).strftime('%Y-%m-%d')
    file_path = generate_file_path(
        provider="mysportsfeeds",
        context="dev",
        dataset_name=f"nhl_{endpoint}",
        schema_version="v2.1",
        date=parsed_date
    )
    save_to_minio(data, "raw-nhl-dfs", file_path, minio_client)
    logger.info(f"Completed ingestion for {endpoint} data on {date}")


@flow(name="ingest-dfs-projections")
def ingest_projections_flow(
        date: str = None,
        season: str = "2024-2025-regular",
        endpoint: str = "dfs_projections",
        creds_path: str = "creds.yml"
) -> None:
    """Prefect Flow for ingesting MySportsFeeds Daily DFS projections data."""
    return ingest_dfs_flow(
        date=date,
        season=season,
        endpoint=endpoint,
        creds_path=creds_path
    )

########################## https://moneypuck.com/data.htm ######################
@task(cache_key_fn=task_input_hash)
def build_moneypuck_url(season_year: str, season_type: str = "regular",
                        dataset: str = "teams") -> str:
    """
    Build MoneyPuck URL for data ingestion

    Parameters:
        season_year: Year of season start (e.g. '2024')
        season_type: Either 'regular' or 'playoffs'
        dataset: The dataset to fetch (default 'teams')

    Returns:
        Full URL for MoneyPuck data
    """
    logger = get_run_logger()
    url = f"https://moneypuck.com/moneypuck/playerData/seasonSummary/{season_year}/{season_type}/{dataset}.csv"
    logger.info(f"Built MoneyPuck URL: {url}")
    return url


@task(retries=3, retry_delay_seconds=60)
def fetch_moneypuck_data(url: str) -> bytes:
    """
    Fetch data from MoneyPuck website.
    Returns raw CSV bytes to preserve original format.
    """
    logger = get_run_logger()

    response = requests.get(url)
    response.raise_for_status()

    logger.info(f"Successfully fetched data from MoneyPuck with status code {response.status_code}")
    return response.content  # Return raw bytes


@flow(name="ingest-moneypuck-teams-stats")
def ingest_moneypuck_teamstats_flow(
        season_year: str = "2024",
        season_type: str = "regular",
        creds_path: str = "creds.yml"
) -> None:
    """Prefect Flow for ingesting MoneyPuck team statistics data."""
    logger = get_run_logger()

    # Initialize MinIO client
    creds = load_credentials(creds_path)
    minio_client = init_minio_client(creds)

    # Execute flow
    url = build_moneypuck_url(season_year, season_type)
    data = fetch_moneypuck_data(url)

    # Generate file path
    parsed_date = datetime.datetime.today().strftime('%Y-%m-%d')
    file_path = generate_file_path(
        provider="moneypuck",
        context="dev",
        dataset_name="moneypuck_team_stats",
        schema_version="unknown",
        date=parsed_date
    ).replace('.json', '.csv')  # Adjust extension for CSV

    # Save raw CSV bytes to MinIO
    minio_client.put_object(
        "raw-nhl-dfs",
        file_path,
        BytesIO(data),
        len(data)
    )
    logger.info(f"Completed ingestion of {season_year} {season_type} season MoneyPuck team stats as of {parsed_date}")


if __name__ == "__main__":
    # Run both flows for current date
    ingest_dfs_flow()  # Uses defaults (current date)
    ingest_projections_flow()  # Uses defaults (current date)
    #TODO: Need to better parameterize different future seasons in prefect
    ingest_moneypuck_teamstats_flow()  # Uses defaults (2024 regular season)
