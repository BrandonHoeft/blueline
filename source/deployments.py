# source/deployments.py
"""
Prefect deployment configuration for NHL DFS data ingestion.
Schedules daily ingestion of DFS data and projections.

Usage:
    python source/deployments.py
"""

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
# local module imports
from source.ingest import ingest_dfs_flow, ingest_projections_flow


def deploy_dfs_flows():
    """
    Create and apply Prefect deployments for DFS data ingestion.
    Schedules:
    - DFS data: Daily at 8am ET
    - DFS projections: Daily at 9am ET
    """
    # Daily DFS data ingestion at 8am ET
    dfs_deployment = Deployment.build_from_flow(
        flow=ingest_dfs_flow,
        name="daily-dfs-ingest",
        parameters={
            "season": "2024-2025-regular",
            "creds_path": "creds.yml"
        },
        schedule=CronSchedule(
            cron="0 8 * * *",
            timezone="America/New_York"
        ),
        tags=["nhl", "dfs", "daily"]
    )

    # Daily DFS projections ingestion at 9am ET
    projections_deployment = Deployment.build_from_flow(
        flow=ingest_projections_flow,
        name="daily-projections-ingest",
        parameters={
            "season": "2024-2025-regular",
            "creds_path": "config/creds.yml"
        },
        schedule=CronSchedule(
            cron="0 9 * * *",
            timezone="America/New_York"
        ),
        tags=["nhl", "dfs", "projections", "daily"]
    )

    # Apply deployments
    dfs_deployment.apply()
    projections_deployment.apply()


if __name__ == "__main__":
    deploy_dfs_flows()