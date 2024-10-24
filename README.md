# BlueLine

NHL daily fantasy sports optimizer. Built in tandem with Claude Projects (3.5 Sonnet) 

# Architecture - Process View
 
```mermaid

flowchart TB
    subgraph Sources
        MSF[MySportsFeeds API]
        MPC[Moneypuck.com]
        DK[DraftKings Bets History]
    end

    subgraph Bronze["Bronze Layer (Raw: JSON, CSV)"]
        direction TB
        RAW_DFS[/"raw-nhl-dfs/
        mysportsfeeds/dev/nhl_dfs_actuals/
        v=2.1/date=YYYY-MM-DD"/]
        RAW_PROJ[/"raw-nhl-dfs/
        mysportsfeeds/dev/nhl_prjctn/
        v=2.1/date=YYYY-MM-DD"/]
        RAW_TEAM[/"raw-nhl-dfs/
        moneypuck.com/dev/team-stats/
        v=2.1/date=YYYY-MM-DD"/]
        RAW_BETS[/"raw-nhl-dfs/
        draftkings/dev/betting-history/
        v=2.1/date=YYYY-MM-DD"/]
    end

    subgraph Silver["Silver Layer (Iceberg Tables)"]
        direction TB
        CLEAN_DFS["Clean DFS Data
        Format: Parquet
        Table Type: Iceberg"]
        CLEAN_PROJ["Clean Projections
        Format: Parquet
        Table Type: Iceberg"]
        CLEAN_TEAM["Clean Team Stats
        Format: Parquet
        Table Type: Iceberg"]
        CLEAN_BETS["Clean DFS Bets
        Format: Parquet
        Table Type: Iceberg"]
    end

    subgraph Gold["Gold Layer (Iceberg Tables)"]
        direction TB
        SLATES["Slates
        Format: Parquet
        Table Type: Iceberg"]
        PLAYER_PERF["Player Performance
        Format: Parquet
        Table Type: Iceberg"]
        PLAYER_PROJ["Player Projections
        Format: Parquet
        Table Type: Iceberg"]
        TEAM_MATCHUPS["Team Matchups
        Format: Parquet
        Table Type: Iceberg"]
        DFS_BETS["DFS Bets
        Format: Parquet
        Table Type: Iceberg"]
        MODEL_PERF["Model Performance
        Format: Parquet
        Table Type: Iceberg"]
        LINEUPS["User Lineups
        Format: Parquet
        Table Type: Iceberg"]
    end

    subgraph Services
        MINIO[(MinIO
        Object Storage)]
        TRINO{{Trino
        Query Engine}}
        HIVE[(Hive Metastore
        Table Metadata)]
        DASH[/Plotly Dash
        Web Interface\]
        OPTIMIZER((Linear
        Optimizer
        Logic))
    end

    MSF --> |"Prefect (Python, DuckDB)"| RAW_DFS
    MSF --> |"Prefect (Python, DuckDB)"| RAW_PROJ
    MPC --> |"Prefect (Python, DuckDB)"| RAW_TEAM
    DK --> |"Prefect (Python, DuckDB)"| RAW_BETS

    RAW_DFS --> |"Prefect (dbt-core)"| CLEAN_DFS
    RAW_PROJ --> |"Prefect (dbt-core)"| CLEAN_PROJ
    RAW_TEAM --> |"Prefect (dbt-core)"| CLEAN_TEAM
    RAW_BETS --> |"Prefect (dbt-core)"| CLEAN_BETS

    CLEAN_DFS --> |"Prefect (dbt-core)"| SLATES
    CLEAN_DFS --> |"Prefect (dbt-core)"| PLAYER_PERF
    CLEAN_PROJ --> |"Prefect (dbt-core)"| PLAYER_PROJ
    CLEAN_TEAM --> |"Prefect (dbt-core)"| TEAM_MATCHUPS
    CLEAN_BETS --> |"Prefect (dbt-core)"| DFS_BETS
    
    SLATES --> |Query| DASH
    PLAYER_PERF --> |Query| DASH
    PLAYER_PROJ --> |Query| DASH
    TEAM_MATCHUPS --> |Query| DASH
    DFS_BETS --> |Query| DASH
    MODEL_PERF --> |Query| DASH
    
    SLATES --> |Input| OPTIMIZER
    PLAYER_PERF --> |Input| OPTIMIZER
    PLAYER_PROJ --> |Input| OPTIMIZER
    TEAM_MATCHUPS --> |Input| OPTIMIZER
    
    OPTIMIZER --> |"Optimized Lineups"| DASH
    DASH --> |Store| LINEUPS
    LINEUPS --> |"Prefect (dbt-core)"| MODEL_PERF
    DFS_BETS --> |"Prefect (dbt-core)"| MODEL_PERF

    MINIO --- |Store| Bronze
    MINIO --- |Store| Silver
    MINIO --- |Store| Gold
    TRINO --- |Query| Gold
    HIVE --- |Metadata| Gold

```