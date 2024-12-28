# scripts/deploy_flows.py
"""
Scheduling the prefect flows, defined in ingest.py, to deploy to my docker
prefect server
"""

import subprocess
from prefect import deploy
from source.common.ingest_utils import (
    ingest_dfs_flow,
    ingest_projections_flow,
    ingest_moneypuck_teamstats_flow
)

# Common parameters for all deployments

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


def create_work_pool():
    """Docs on this: https://orion-docs.prefect.io/latest/tutorial/work-pools/"""
    subprocess.run(["prefect", "work-pool", "create", "blueline-ingestion-pool", "--type",
                    "docker"], check=True)

if __name__ == "__main__":
    #create_work_pool()  # Create the work pool: blueline-ingestion-pool
    deploy(
        # Use the `to_deployment` method to specify configuration
        # specific to each deployment
        ingest_dfs_flow.to_deployment("ingest-dfs-flow-deployment",
                                      parameters=MSF_DFS_PARAMS
                                  ),
        ingest_projections_flow.to_deployment(name="ingest-projections-flow-deployment",
                                              parameters=MSF_DFS_PROJECTIONS_PARAMS
                                          ),
        ingest_moneypuck_teamstats_flow.to_deployment(
            name="ingest-moneypuck-teamstats-flow-deployment",
            parameters=MONEYPUCK_PARAMS
            ),

        # Specify shared configuration for both deployments
        image="blueline-ingestion:dev",
        push=False,
        work_pool_name="blueline-ingestion-pool",
    )
