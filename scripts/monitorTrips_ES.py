from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from pandas.io.json import json_normalize

import json
import requests
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta 
import os, time
import pytz

from elasticsearch import Elasticsearch
from apscheduler.schedulers.background import BackgroundScheduler


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

def get_vehicles(feed_obj):
    # check if empty
    if len(feed_obj) > 0:
        # get the trip updates listed on the feed
        vehicles = [vehicle for vehicle in feed_obj['entity'] if 'vehicle' in vehicle]
        return vehicles
    else:
        return None

def updates_to_dataframe(updates):
    # transform feed to a dataframe 
    df = json_normalize(updates)
    df['tripUpdate.stopTimeUpdate'] = df['tripUpdate.stopTimeUpdate'].apply(lambda x: x[0])
    print("length of updates: {}".format(len(updates))) # debug: print number of updates in the feed
    
    # format feed
    x = json_normalize(df['tripUpdate.stopTimeUpdate'])
    x['tripUpdate.trip.tripId'] = df['tripUpdate.trip.tripId']
    x['tripUpdate.timestamp'] = df['tripUpdate.timestamp']
    x['tripUpdate.delay'] = df['tripUpdate.delay']
    x['id'] = df['id']

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

def insertToES(df, index, id):
    es=Elasticsearch([{'host':'localhost','port':9200, 'http_auth':('elastic', 'changeme')}])
    for idx, record in enumerate(df.to_dict(orient='records'), 1):
        es.index(index=index,doc_type='lightrail',body=record, id=record[id])
        print('inserted: ', record['Feed ID'])

def start_monitoring():
    print('\nMonitoring started\n---------------------')
    
    feed = get_feed() # get raw feed
    updates = get_updates(feed) # get trip updates
    vehicles = get_vehicles(feed) # get vehicles
    
    if validate(updates):

        df = updates_to_dataframe(updates) # transform updates to dataframe
        
        # rename trip upates dataframe
        df.columns = ['Arrival Delay', 'Arrival Time', 'Arrival Uncertainty',
       'Departure Delay', 'Departure Time', 'Departure Uncertainty',
       'Schedule Relationship', 'Stop ID', 'Stop Sequence', 'Trip ID',
       'Request Timestamp', 'Delay', 'Feed ID']

        start = datetime.datetime.now() - datetime.timedelta(minutes=1) # setting time range start
        end = datetime.datetime.now() + datetime.timedelta(minutes=1) # setting time range end
        
        start = datetime.datetime.strftime(start, '%H:%M')
        end = datetime.datetime.strftime(end, '%H:%M')
        print( start, end )
        
        # set the Arrival time as index to use between_time function
        records = df.set_index('Arrival Time')
        records = records.between_time(start, end)
        records.reset_index(inplace=True)

        # change the datetime to epoch
        records['Arrival Time'] = records['Arrival Time'].apply(lambda x: int(time.mktime(x.timetuple())))
        records['Departure Time'] = records['Departure Time'].apply(lambda x: int(time.mktime(x.timetuple())))
        records['Request Timestamp'] = records['Request Timestamp'].apply(lambda x: int(time.mktime(x.timetuple())))

        records['Arrival Time'] = pd.to_datetime(records['Arrival Time'], unit='s')
        records['Departure Time'] = pd.to_datetime(records['Departure Time'], unit='s')
        records['Request Timestamp'] = pd.to_datetime(records['Request Timestamp'], unit='s')

        # get the dataframe of vehicles from the feed update
        vehicles = json_normalize(vehicles)
        vehicles.columns = ['Feed ID', 'isDeleted', 'Congestion Level', 'Current Status', 'Current Stop Sequence', 'Occupancy Status', 
        'Bearing', 'Latitude', 'Longitude', 'Odometer', 'Speed', 'Stop Id', 'Timestamp', 'Trip Id', 'Vehicle Id', 'Vehicle Label', 'Vehicle License Plate']
        vehicles.drop(columns='Stop Id', axis=1, inplace=True)

        # insert the records to elasticsearch
        insertToES(records, index='trips', id='Feed ID')
        insertToES(vehicles, index='vehicles', id='Feed ID')
         
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