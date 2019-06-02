# coding: utf-8
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from pandas.io.json import json_normalize
from apscheduler.schedulers.background import BackgroundScheduler

# from sqlalchemy import inspect
# from sqlalchemy import MetaData
# from sqlalchemy import Table
# import sqlalchemy as db

import json
import requests
import numpy as np
import pandas as pd
import datetime
import os, time
import pytz


def get_feed():
    # initialise the feed message parser from Google
    feed = gtfs_realtime_pb2.FeedMessage()

    # get the response from the api
    response = requests.get('http://files.transport.act.gov.au/feeds/lightrail.pb', allow_redirects=True)

    # pass the response to the Parser
    feed.ParseFromString(response.content)

    # convert to dict from our original protobuf feed
    dict_obj = MessageToDict(feed)

    return dict_obj


def get_updates(feed_obj):
    # check if empty
    if len(feed_obj) > 0:
        # get the trip updates listed on the feed
        updates = [update for update in feed_obj['entity'] if 'tripUpdate' in update]
        return updates
    else:
        return None


def updates_to_dataframe_old(updates):
    # transform feed to a data frame
    df = json_normalize(updates)
    df.columns = ['ID', 'Trip Update', 'Request Timestamp', 'Trip ID']
    df['Request Timestamp'] = pd.to_datetime(df['Request Timestamp'], unit='s')

    # parse Trip Update column
    df['Trip Update'] = df['Trip Update'].apply(lambda x: x[0])
    df_2 = json_normalize(df['Trip Update'])

    # change arrival time and departure time to datetime
    df_2['arrival.time'] = pd.to_datetime(df_2['arrival.time'], unit='s')
    df_2['departure.time'] = pd.to_datetime(df_2['departure.time'], unit='s')

    # combine data frames
    updates_df = pd.concat([df, df_2], axis=1)
    updates_df.rename(inplace=True, columns=
    {
        'arrival.time': 'Arrival Time',
        'arrival.delay': 'Arrival Delay',
        'departure.time': 'Departure Time',
        'departure.delay': 'Departure Delay'
    })

    # drop unnecessary colimns
    updates_df.drop(['ID', 'Trip Update', 'arrival.uncertainty', 'departure.uncertainty'], axis=1, inplace=True)

    # set time zone
    updates_df['Request Timestamp'] = updates_df['Request Timestamp'].dt.tz_localize('UTC').dt.tz_convert(
        'Australia/Canberra')
    updates_df['Arrival Time'] = updates_df['Arrival Time'].dt.tz_localize('UTC').dt.tz_convert('Australia/Canberra')
    updates_df['Departure Time'] = updates_df['Departure Time'].dt.tz_localize('UTC').dt.tz_convert(
        'Australia/Canberra')

    return updates_df


def updates_to_dataframe(updates):
    # transform feed to a dataframe
    df = json_normalize(updates)
    df['tripUpdate.stopTimeUpdate'] = df['tripUpdate.stopTimeUpdate'].apply(lambda x: x[0])
    print("length of updates: {}".format(len(updates)))  # debug: print number of updates in the feed

    # format feed
    x = json_normalize(df['tripUpdate.stopTimeUpdate'])
    x['tripUpdate.trip.tripId'] = df['tripUpdate.trip.tripId']
    x['tripUpdate.timestamp'] = df['tripUpdate.timestamp']
    x['tripUpdate.delay'] = df['tripUpdate.delay']

    # format date time
    x['arrival.time'] = x['arrival.time'].apply(lambda xx: datetime.datetime.fromtimestamp(int(xx)))
    x['departure.time'] = x['departure.time'].apply(lambda xx: datetime.datetime.fromtimestamp(int(xx)))
    x['tripUpdate.timestamp'] = x['tripUpdate.timestamp'].apply(lambda xx: datetime.datetime.fromtimestamp(int(xx)))

    # transform to datetime
    x['arrival.time'] = pd.to_datetime(x['arrival.time'])
    x['departure.time'] = pd.to_datetime(x['departure.time'])
    x['tripUpdate.timestamp'] = pd.to_datetime(x['tripUpdate.timestamp'])

    return x


def validate(updates):
    if updates is None:
        print('Feed is empty')
        return False

    else:
        return True


def start_monitoring():
    print('\nMonitoring started\n---------------------')

    feed = get_feed()  # get raw feed
    updates = get_updates(feed)  # get trip updates
    dir = os.listdir()
    if validate(updates):
        df = updates_to_dataframe(updates)  # transform updates to dataframe
        for i in range(300):
            if 'updates' + str(i) + '.csv' in dir:
                continue
            else:
                df.to_csv('updates' + str(i) + '.csv', index=False)
                break
    else:
        print('To be continued')


def schedule_monitoring():
    scheduler = BackgroundScheduler()
    scheduler.start()
    job = scheduler.add_job(start_monitoring, 'interval', seconds=15)
    print("job details: {}".format(job))
    return scheduler


if __name__ == "__main__":
    scheduler = schedule_monitoring()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()


