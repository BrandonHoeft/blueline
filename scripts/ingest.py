import base64
import json
import requests
import datetime
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

def build_url(season, date, endpoint, data_format='json'):
    base_url = 'https://api.mysportsfeeds.com/v2.1/pull/nhl'
    #compiled_url = base_url + '/' + season + '/date/' + date + '/' + endpoint + '.' + format
    compiled_url = f"{base_url}/{season}/date/{date}/{endpoint}.{data_format}"
    return compiled_url

def fetch_data(url, key, pw):
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
        elif response.status_code == 500:
            print("Ruh Roh! An internal error has occurred, and has been logged for further inspection.")
        elif response.status_code in [499, 502, 503]:
            print("Ruh Roh! Server error. These errors can occur periodically and usually resolve themselves in a matter of seconds.")
        else:
            print(f"Ruh Roh! Unexpected response code: {response.status_code}")
            print(f"Ruh Roh! Response text: {response.text}")

# Example usage

dfs_url = build_url('2023-2024-regular', '20231130', 'dfs')  # list of slates with games/contests/players, including salaries and fantasy points
dfs_prjctn_url = build_url('2023-2024-regular', '20231130', 'dfs_projections')  # Lists all players who *could* play, along with their projected fantasy points, for each supported DFS source.
# Example usage
apikey_token = creds['msf']['key']
password = creds['msf']['password']

dfs_data = fetch_data(dfs_url, apikey_token, password)
prjctn_data = fetch_data(dfs_prjctn_url, apikey_token, password)


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