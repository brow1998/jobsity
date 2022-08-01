import argparse
import json
import logging
from uuid import uuid4
from glob import glob
import pandas as pd
from confluent_kafka import Producer
from datetime import datetime

from multi import run_task

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

KAFKA_TOPIC_NAME = "trips"


def delivery_report(errmsg, msg):
    if errmsg is not None:
        logging.error(f"Delivery failed - Message: {msg.key()} : {errmsg}")
        return

    logging.info(
        f"Message: {msg.key()} successfully produced to Topic: {msg.topic()} Partition: [{msg.partition()}] at offset {msg.offset()}")


def send_to_kafka(row):
    producer.produce(topic=KAFKA_TOPIC_NAME, key=str(uuid4()),
                     value=json.dumps(row), on_delivery=delivery_report)


start_time = datetime.now()
logging.info("Starting Kafka Producer...")

conf = {
    'bootstrap.servers': 'localhost:9092',
}

logging.info("connecting to Kafka topic...")
producer = Producer(conf)

producer.poll(0)

for file in glob('data/*.csv'):
    logging.info(f"Reading data from {file}...")
    df = pd.read_csv(file, chunksize=100_000, names=['region','origin_coord','destination_coord','date_time','datasource'])
    for data in df:
        rows = data.to_dict(orient='records')
        run_task(send_to_kafka, rows)
        producer.flush()
    logging.info("Processing...")
    logging.info(f"File {file} processed successfully!")

end_time = datetime.now()

logging.info(f"Process completed after {end_time - start_time}")