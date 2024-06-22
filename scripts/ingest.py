import json
import requests
import datetime
from minio import Minio
from io import BytesIO
from ohmysportsfeedspy import MySportsFeeds
from prefect import task, Flow
from typing import Dict, Any
import yaml

# Load credentials from creds.yml
with open("creds.yml", 'r') as ymlfile:
    creds = yaml.safe_load(ymlfile)

# Initialize MinIO client
minio_client = Minio(
    creds['minio']['endpoint'],
    access_key=creds['minio']['access_key'],
    secret_key=creds['minio']['secret_key'],
    secure=False
)

def fetch_msf_data(version: str, league: str, season: str, feed: str, date: str, format: str = 'json') -> Dict:
    msf = MySportsFeeds(version=version)
    msf.authenticate(creds['msf']['private_key'], creds['msf']['password'])

    try:
        data = msf.msf_get_data(league=league, season=season, feed=feed, date=date, format=format)
    except Exception as e:
        print("Error:", e)
    finally:
        print(type(data))

data = fetch_msf_data("2.1", league='nhl', season='2023-regular', feed='daily_dfs', date='20231011', format='json')

def fetch_data(api_url: str) -> Dict[str, Any]:
    response = requests.get(api_url)
    data = response.json()
    return data

def generate_file_path(provider: str, context: str, dataset_name: str,
                       schema_version: str) -> str:
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    file_path = f"{provider}/{context}/{dataset_name}/v={schema_version}/date={today}/{dataset_name}_{today}.json"
    return file_path

def save_raw_to_minio(data: Dict[str, Any], bucket_name: str,
                      object_name: str) -> None:
    raw_data = json.dumps(data).encode('utf-8')
    minio_client.put_object(bucket_name, object_name, BytesIO(raw_data),
                            len(raw_data))


# Define the flow
with Flow("ETL Flow") as flow:
    api_url_dfs = "https://api.mysportsfeeds.com/v2.1/pull/nhl/2023-2024-regular/date/20231011/dfs.json"
    api_url_dfs_projections = "https://api.mysportsfeeds.com/v2.1/pull/nhl/2023-2024-regular/date/20231011/dfs_projections.json"

    # Fetch data
    raw_data_dfs = fetch_data(api_url_dfs)
    raw_data_dfs_projections = fetch_data(api_url_dfs_projections)

    # Generate file paths
    file_path_dfs = generate_file_path("mysportsfeeds", "prod", "nhl_dfs",
                                       "v2.1")
    file_path_dfs_projections = generate_file_path("mysportsfeeds", "prod",
                                                   "nhl_dfs_projections",
                                                   "v2.1")

    # Save raw data to MinIO
    save_raw_to_minio(raw_data_dfs, "raw-bucket", file_path_dfs)
    save_raw_to_minio(raw_data_dfs_projections, "raw-bucket",
                      file_path_dfs_projections)

# Run the flow
flow.run()
