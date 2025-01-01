"""
Prefect flow for ingesting MoneyPuck team statistics data.
This flow handles CSV data ingestion from MoneyPuck's public
NHL team aggregated statistics
"""

import datetime
import requests
from io import BytesIO
from prefect import task, flow, get_run_logger
import pytz
from prefect.tasks import task_input_hash
from source.common.ingest_utils import (
    load_credentials,
    init_minio_client,
    generate_file_path
)


@task
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


@flow(name="ingest-moneypuck-teamstats-flow")
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
    chicago_tz = pytz.timezone('America/Chicago')  # in case running this ~11pm CDT/CST ever. don't want date to round to next day if it's eastern time
    parsed_date = datetime.datetime.now(tz=chicago_tz).strftime('%Y-%m-%d')
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
    # Both Option 1 & 2 will work if running python-dev 3.11 container as interpreter, docker-compose.yml
    # env variable PREFECT_API_URL integrates this interpreter with containerized prefect server.

    # Option 1: Run flow directly
    # ingest_moneypuck_teamstats_flow()

    # Option 2: Deploy flow to Prefect server
    # hack: serve() is a process that remains open and long running. run it from a python-dev container process
    ingest_moneypuck_teamstats_flow.serve(
        name="ingest-moneypuck-teamstats-flow-deployment",
        parameters={
            "season_year": "2024",
            "season_type": "regular",
            "creds_path": "creds.yml"
        },
    )
