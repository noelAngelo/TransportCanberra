# coding: utf-8
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from pandas.io.json import json_normalize
from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy import inspect
from sqlalchemy import MetaData
from sqlalchemy import Table
import sqlalchemy as db

import json
import requests
import numpy as np
import pandas as pd
import datetime
import os, time

def get_positions(feed_obj):
    # get the position of the vehicles listed in the feed
    vehicles = [vehicle for vehicle in feed_obj['entity'] if 'vehicle' in vehicle]
    vehicle_positions = json_normalize(vehicles)

    # clean the realtime feed
    try:
        vehicle_positions = vehicle_positions.dropna(subset=['vehicle.trip.tripId', 'vehicle.currentStopSequence'])
    except:
        pass
    vehicle_positions = vehicle_positions.where((pd.notnull(vehicle_positions)), None)
    try:
        vehicle_positions.drop('vehicle.currentStatus', axis=1, inplace=True)
    except:
        pass

    return vehicle_positions

def start_monitoring():
    print('Monitoring has started')

    # initialise the feed message parser from Google
    feed = gtfs_realtime_pb2.FeedMessage()

    # get the response from the api
    response = requests.get('http://files.transport.act.gov.au/feeds/lightrail.pb', allow_redirects=True)

    # pass the response to the Parser
    feed.ParseFromString(response.content)

    # convert to dict from our original protobuf feed
    dict_obj = MessageToDict(feed)

    # prepare rows to insert
    vehicle_positions = get_positions(dict_obj)
    try:
        vehicle_positions.drop('vehicle.currentStatus', axis=1, inplace=True)
    except:
        pass

    engine = db.create_engine('postgresql://postgres@localhost:5432/noelangelo')
    vehicles_db = pd.read_sql_table('vehicles', engine)

    cols = ['id','congestionLevel','currentStopSequence','latitude','longitude','odometer','speed','timestamp','tripId','vehicleId','vehicleLabel','vehiclePlate']
    vehicle_positions.columns = cols
    df = vehicle_positions[~vehicle_positions['id'].isin(vehicles_db['id'])]
    df = df.reset_index(drop = True)
    rows = df.to_dict(orient='id')
    vehicle_list = [rows[idx] for idx, val in enumerate(rows)]
    length = len(vehicle_list)

    return vehicle_list

def writeToPostgres(vehicle_list):
    # Initiate Sqlalchemy - Postgres engine
    engine = db.create_engine('postgresql://postgres@localhost:5432/noelangelo')

    # Get Table from Postgres
    vehicles_db = pd.read_sql_table('vehicles', engine)

    # initiate metadata for insertion
    metadata = MetaData(engine, reflect=True)
    connection = engine.connect()
    vehicle_pos = metadata.tables['vehicles']

    ResultProxy = connection.execute(vehicle_pos.insert(),vehicle_list)

    # DEBUG:
    print('Count: {}'.format(len(vehicle_list)))
    for vehicle in vehicle_list:
        print(' ID: {}, Trip Id: {}, VehicleId: {}, StopSequence: {}'.format(vehicle['id'], vehicle['tripId'], vehicle['vehicleId'], vehicle['currentStopSequence']))

def schedule_monitoring():
    p = start_monitoring()
    writeToPostgres(p)


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.start()
    job = scheduler.add_job(schedule_monitoring, 'interval', seconds=15)

    print("job details: {}".format(job))

    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
