"""
Prefect flow for ingesting MySportsFeeds DFS Projections data.
This flow handles the projections data (predicted Draftkings points)
from the MySportsFeeds API.
"""

import datetime
import dateutil.parser as dparser
from prefect import flow, get_run_logger
from source.common.ingest_utils import (
    load_credentials,
    init_minio_client,
    build_msf_url,
    fetch_msf_data,
    generate_file_path,
    save_to_minio
)

@flow(name="ingest-msf-projections-flow")
def ingest_msf_projections_flow(
        date: str = datetime.datetime.today().strftime('%Y%m%d'),
        season: str = "2024-2025-regular",
        endpoint: str = "dfs_projections",
        creds_path: str = "creds.yml"
) -> None:
    """
    Prefect Flow for ingesting MySportsFeeds DFS Projections data.

    Parameters
    ----------
    date: Date to fetch data for (default: today)
    season: NHL season identifier
    endpoint: API endpoint to use
    creds_path: Path to credentials file
    """
    logger = get_run_logger()

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


if __name__ == "__main__":
    # Both Option 1 & 2 will work if running python-dev 3.11 container as interpreter, per docker-compose.yml
    # env variable PREFECT_API_URL integrates this interpreter with containerized prefect server.

    # Option 1: Run flow directly
    # ingest_projections_flow()

    # Option 2: Deploy flow to Prefect server
    # hack: serve() is a process that remains open and long running. run it from a python-dev container process
    ingest_msf_projections_flow.serve(
        name="ingest-msf-projections-flow-deployment",
        parameters={
            "date": datetime.datetime.today().strftime('%Y%m%d'),
            "season": "2024-2025-regular",
            "endpoint": "dfs_projections",
            "creds_path": "creds.yml"
        }
    )
