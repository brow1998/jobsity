from confluent_kafka import Consumer
import time
from clickhouse_driver import Client
import json
import shapely.wkt
import re
from datetime import datetime
import logging

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

logging.info("Starting Kafka Consumer")

conf = {
        'bootstrap.servers' : 'localhost:9092',
        'group.id' : 'main_group',
        'auto.offset.reset' : 'earliest',
        'enable.auto.commit' : True,
        }

logging.info("connecting to Kafka topic")

consumer = Consumer(conf)
client = Client('localhost')


consumer.subscribe(['trips'])

while True:
    msg = consumer.poll(0.5)

    if msg is None:
        continue
    if msg.error():
        logging.info("Consumer error happened: {}".format(msg.error()))
        continue

    row = msg.value().decode()
    row = json.loads(row)

    for key in row.keys():
        if 'coord' in key:
            row[key] = tuple([float(i) for i in re.findall(r'[0-9-\.]+', row[key])])
        if 'date_time' in key:
            row[key] = datetime.strptime(row[key], '%Y-%m-%d %H:%M:%S')

    client.execute('INSERT INTO trips VALUES',[row])

    logging.info("Connected to Topic: {} and Partition : {}".format(msg.topic(), msg.partition() ))
    logging.info("Received Message : {} with Offset : {}".format(msg.value().decode('utf-8'), msg.offset() ))
