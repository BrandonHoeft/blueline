import base64
import json
import requests
import datetime
import dateutil.parser as dparser
from minio import Minio
from io import BytesIO
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

def build_url(season: str, date: str, endpoint: str, format: str = 'json') -> str:
    """
    Parameters
    ----------
    season
        like ''2023-2024-regular' or '2024-playoff'
    date
        a valid date in the form of YYYYMMDD
    endpoint
        'dfs' has list of slates with games/contests/players, including salaries and fantasy points
        'dfs_dfs_projections' lists all players who *could* play, along with their projected fantasy points
    format
        'json', 'csv', or 'xml'
    """
    base_url = 'https://api.mysportsfeeds.com/v2.1/pull/nhl'
    compiled_url = f"{base_url}/{season}/date/{date}/{endpoint}.{format}"
    return compiled_url

def fetch_data(url: str, key : str, pw: str) -> Dict[str, Any]:
    # Define the headers with the API key and password encoded in Base64
    headers = {
        "Authorization": "Basic " + base64.b64encode(f'{key}:{pw}'.encode('utf-8')).decode('ascii')
    }

    # Define the parameters for the request
    params = {
        'dfstype': 'draftkings'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        print(f'Response HTTP Status Code: {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f"Ruh Roh! HTTP Request failed: {e}")
        return None
    finally:
        if response.status_code == 200:
            response_data = response.json()
            return response_data
        elif response.status_code == 204:
            print("Ruh Roh! Feed content not found. There is no available content for the feed as of yet.")
        elif response.status_code == 304:
            print("Ruh Roh! Feed content has not changed since your last request.")
        elif response.status_code in [400, 404]:
            print("Ruh Roh! Bad request. The request is malformed.")
        elif response.status_code == 401:
            print("Ruh Roh! Not authenticated. You need to authenticate each request using your HTTP BASIC-encoded MySportsFeeds username/password.")
        elif response.status_code == 403:
            print("Ruh Roh! Not authorized. Indicates you're attempting to access a feed for the current in-progress season, without a proper subscription.")
        elif response.status_code == 429:
            print("Ruh Roh! Too many requests. The API limits excessive overuse.")
        elif response.status_code in [499, 502, 503]:
            print("Ruh Roh! Server error. These errors can occur periodically and usually resolve themselves in a matter of seconds.")
        else:
            print(f"Ruh Roh! Unexpected response code: {response.status_code}")
            print(f"Ruh Roh! Response text: {response.text}")

def generate_file_path(provider: str, context: str, dataset_name: str,
                       schema_version: str, date: str) -> str:
    #TODO: Update this
    # today = datetime.datetime.today().strftime("%Y-%m-%d")
    file_path = f"{provider}/{context}/{dataset_name}/v={schema_version}/date={date}/{dataset_name}_{date}.json"
    return file_path

def setup_bucket(bucket_name: str) -> None:
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    # TODO: Update for bucket versioning
    # minio_client.set_bucket_versioning(bucket_name, "Enabled")

def save_raw_to_minio(data: Dict[str, Any], bucket_name: str,
                      object_name: str) -> None:
    setup_bucket(bucket_name)
    raw_data = json.dumps(data).encode('utf-8')
    minio_client.put_object(bucket_name, object_name, BytesIO(raw_data),
                            len(raw_data))

if __name__ == "__main__":
    # Example usage
    date_str = '20231130'
    date = dparser.parse(date_str)
    date = date.strftime('%Y-%m-%d')

    dfs_url = build_url('2023-2024-regular', date_str, 'dfs')
    dfs_prjctn_url = build_url('2023-2024-regular', date_str, 'dfs_projections')
    # Example usage
    apikey_token = creds['msf']['key']
    password = creds['msf']['password']

    raw_dfs_actuals = fetch_data(dfs_url, apikey_token, password)
    fp_dfs_actuals = generate_file_path("mysportsfeeds", "dev", "nhl_dfs_actuals", "v2.1", date)
    save_raw_to_minio(raw_dfs_actuals, "raw-nhl-dfs", fp_dfs_actuals)

    raw_dfs_prjctns = fetch_data(dfs_prjctn_url, apikey_token, password)
    fp_dfs_prjctns = generate_file_path("mysportsfeeds", "dev", "nhl_prjctn", "v2.1", date)
    save_raw_to_minio(raw_dfs_prjctns, "raw-nhl-dfs", fp_dfs_prjctns)

# Define the flow

