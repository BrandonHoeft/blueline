# scripts/deploy_flows.py
"""
Scheduling the prefect flows, defined in ingest.py, to deploy to my docker
prefect server
"""

from prefect.client.schemas.schedules import CronSchedule
from source.ingest import (
    ingest_dfs_flow,
    ingest_projections_flow,
    ingest_moneypuck_teamstats_flow
)

# Common parameters for all deployments
CRON_SCHEDULE = "0 11 * 10-12,1-6 *"  # 11am Chicago time, Oct-June

# Flow parameters with defaults
MSF_DFS_PARAMS = {
    "season": "2024-2025-regular",
    "endpoint": "dfs",
    "creds_path": "creds.yml"
}

MSF_DFS_PROJECTIONS_PARAMS = {
    "season": "2024-2025-regular",
    "endpoint": "dfs_projections",
    "creds_path": "creds.yml"
}

MONEYPUCK_PARAMS = {
    "season_year": "2024",
    "season_type": "regular",
    "creds_path": "creds.yml"
}

if __name__ == "__main__":
    ingest_dfs_flow.serve(name="ingest-dfs-flow-deployment",
                          schedules=[CronSchedule(cron=CRON_SCHEDULE, timezone="America/Chicago")],
                          parameters=MSF_DFS_PARAMS)

    ingest_projections_flow.serve(name="ingest-projections-flow-deployment",
                                  schedules=[CronSchedule(cron=CRON_SCHEDULE, timezone="America/Chicago")],
                                  parameters=MSF_DFS_PROJECTIONS_PARAMS)

    ingest_moneypuck_teamstats_flow.serve(name="ingest-moneypuck-teamstats-flow-deployment",
                                          schedules=[CronSchedule(cron=CRON_SCHEDULE, timezone="America/Chicago")],
                                          parameters=MONEYPUCK_PARAMS)
