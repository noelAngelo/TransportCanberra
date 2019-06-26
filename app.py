# Import libraries
from pandas.io.json import json_normalize
from sodapy import Socrata
from elasticsearch import Elasticsearch

import json
import requests
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta
import os, time
import pytz
import arrow

# get credentials
with open('.credentials') as f:
    credentials = f.readlines()
    credentials = json.loads(''.join(credentials).strip())


# -- HELPER FUNCTIONS
def get_realtime_feed():
    # authenticate Socrata
    client = Socrata('www.data.act.gov.au', '4jqogoRJ9NKj1gr8QAZ9CCKFI',
                     username=credentials['username'],
                     password=credentials['password'])
    # get endpoint
    results = client.get("r9a8-xw6s")
    # Convert to pandas DataFrame
    results_df = pd.DataFrame.from_records(results)
    return results_df


# adds information from trips.csv and stops.csv
def update_feed(dff, trips, stops):
    # TODO: check with Selva later for R (reserved buses) but removing them for now
    dff = dff[dff['trip_id'].map(lambda x: 'R' not in x)]

    # convert columns to datetime and int
    dff['arrival_delay'] = dff['arrival_delay'].astype(int)
    dff['depature_delay'] = dff['depature_delay'].astype(int)
    dff['stop_sequence'] = dff['stop_sequence'].astype(int)
    dff['trip_id'] = dff['trip_id'].astype(int)
    trips['trip_id'] = trips['trip_id'].astype(int)
    stops['stop_id'] = stops['stop_id'].astype(str)

    dff['arrival_time'] = dff['arrival_time'].apply(lambda x: arrow.get(x, tzinfo='Australia/Canberra'))
    dff['depature_time'] = dff['depature_time'].apply(lambda x: arrow.get(x, tzinfo='Australia/Canberra'))
    dff['timestamp'] = dff['timestamp'].apply(lambda x: arrow.get(x, tzinfo='Australia/Canberra'))

    # sort columns based on arrival time
    dff = dff.sort_values(by='arrival_time', ascending=True)

    # drop columns
    dff = dff[
        ['arrival_delay', 'arrival_time', 'depature_delay', 'depature_time', 'stop_id',
         'stop_sequence', 'trip_id', 'timestamp']]
    trips = trips[['route_id', 'service_id', 'trip_id', 'trip_headsign', 'direction_id']]
    stops = stops[stops.columns[:2]]

    # merge columns
    merged = pd.merge(left=stops, left_on='stop_id', right=dff, right_on='stop_id', how='right')
    merged = pd.merge(left=trips, left_on='trip_id', right=merged, right_on='trip_id', how='right')
    # print('|     Dates    |\n----------------')
    # for i in sorted(merged['arrival_date'].unique()):
    #     print('|  {}  |'.format(str(i)))
    return merged


# schedule routine to push data to Elasticsearch
def push_to_es(dff, es):
    records_list = dff.to_dict(orient='records')
    if len(records_list) == 0:
        print('empty records')
        return False
    else:
        print('\nRecorded:')
        prev_record = 0
        for record in records_list:
            if prev_record == record['trip_id']:
                continue
            else:
                print("- Trip Id: {}".format(record['trip_id']))
                es.index(index='trips_realtime', doc_type='lightrail', body=record)
        print("* * * *")
        return True


# -- END HELPER FUNCTIONS


# Main Function
if __name__ == '__main__':
    # print('Running app . . .')
    # get data from trips and stops
    trip_df = pd.read_csv('./GTFS/google_transit_lr/trips.csv')
    stop_df = pd.read_csv('./GTFS/google_transit_lr/stops.csv')

    # elasticsearch default configuration
    es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'http_auth': ('elastic', 'changeme')}])

    # schedule to pull 2 datasets with a 15 second interval and compare
    while True:
        # print('Calling early')
        early_call = update_feed(get_realtime_feed(), trip_df, stop_df)
        time.sleep(15)
        now = arrow.now()
        # print('Calling late')
        late_call = update_feed(get_realtime_feed(), trip_df, stop_df)
        # compare combined dataframes
        df = pd.concat([late_call, early_call])
        df.sort_values(by='trip_id', inplace=True)
        df.drop_duplicates(subset=['trip_id', 'arrival_time'], inplace=True)
        filtered_df = df[df['depature_time'].map(lambda x: (now - x).seconds <= 15)]
        filtered_df['arrival_time'] = filtered_df['arrival_time'].apply(lambda x: x.datetime)
        filtered_df['depature_time'] = filtered_df['depature_time'].apply(lambda x: x.datetime)
        filtered_df['timestamp'] = filtered_df['timestamp'].apply(lambda x: x.datetime)
        # push data to elastic
        push_to_es(filtered_df, es)
