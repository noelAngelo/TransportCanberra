import time
import datetime
import json

from sodapy import Socrata
from confluent_kafka import Producer

class lrRealTime(object):

    def __init__(self):
        with open('.tc_api_key', 'r') as key:
            self.api_key = key.read().strip()
        self.tc_api_url = 'www.data.act.gov.au'
        self.kafka_topic = 'test_openData'
        self.kafka_producer = Producer({'bootstrap.servers': 'localhost:9092'})

    def produce_trip_updates(self):
        client = Socrata(self.tc_api_url,
                self.api_key)
        response = client.get("4f7h-bvpk", limit=2000)