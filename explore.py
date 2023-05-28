import os

from ohmysportsfeedspy import MySportsFeeds
import pandas as pd

msf = MySportsFeeds(version="2.1")

API_KEY = os.environ.get("API_KEY")
PW = os.environ.get("PW")

msf.authenticate(API_KEY, PW)

output = msf.msf_get_data(league='nhl', season='2022-2023-regular', feed='daily_team_gamelogs', date='20221012', format='json')

df = pd.json_normalize(output, record_path=['gamelogs'], meta='lastUpdatedOn')

print(df.shape)

