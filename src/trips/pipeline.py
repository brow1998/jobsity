"""Produce trip events to Kafka and sink them into ClickHouse.

Delivery is at-least-once end to end: the producer waits for every ack, and the consumer
commits its Kafka offsets only after ClickHouse accepted the batch. Duplicates that this
allows are collapsed by ClickHouse, because `trips` is a ReplacingMergeTree keyed by the
content-derived `trip_id`.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime

import clickhouse_connect
from confluent_kafka import Consumer, KafkaException, Producer

from trips.parse import Rejected, read_events

log = logging.getLogger(__name__)

TOPIC = "trips"
COLUMNS = [
    "trip_id",
    "region",
    "origin_lon",
    "origin_lat",
    "destination_lon",
    "destination_lat",
    "date_time",
    "datasource",
    "source_file",
    "source_line",
    "kafka_partition",
    "kafka_offset",
]


def kafka_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


def clickhouse():
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "8123")),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
    )


@dataclass
class IngestReport:
    sent: int = 0
    delivered: int = 0
    failed: int = 0
    rejected: list[Rejected] = field(default_factory=list)


def ingest(paths: list[str]) -> IngestReport:
    """Send every valid row of every file to Kafka and wait until each one is acknowledged."""
    report = IngestReport()
    producer = Producer({"bootstrap.servers": kafka_servers(), "enable.idempotence": True})

    def on_delivery(error, _message):
        if error:
            report.failed += 1
            log.error("delivery failed: %s", error)
        else:
            report.delivered += 1
            if report.delivered % 10_000 == 0:
                log.info("delivered %d", report.delivered)

    for path in paths:
        for item in read_events(path):
            if isinstance(item, Rejected):
                report.rejected.append(item)
                log.warning("rejected %s:%d: %s", item.source_file, item.source_line, item.reason)
                continue
            while True:
                try:
                    producer.produce(TOPIC, key=item["trip_id"], value=json.dumps(item), on_delivery=on_delivery)
                    break
                except BufferError:  # local queue full: let deliveries drain, then retry
                    producer.poll(0.5)
            report.sent += 1
            producer.poll(0)

    remaining = producer.flush(60)
    report.failed += remaining
    return report


def sink(idle_seconds: float = 5.0, batch_size: int = 10_000) -> int:
    """Consume until the topic stays quiet for `idle_seconds`. Returns rows written."""
    consumer = Consumer(
        {
            "bootstrap.servers": kafka_servers(),
            "group.id": "clickhouse-sink",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([TOPIC])
    client = clickhouse()
    written, last_message = 0, time.monotonic()
    try:
        # Joining the consumer group can take a while, so allow longer before the first message.
        while time.monotonic() - last_message < (idle_seconds if written else max(idle_seconds, 30.0)):
            messages = consumer.consume(batch_size, timeout=1.0)
            if not messages:
                continue
            last_message = time.monotonic()
            rows = []
            for m in messages:
                if m.error():
                    raise KafkaException(m.error())
                event = json.loads(m.value())
                event["date_time"] = datetime.fromisoformat(event["date_time"])
                rows.append([*(event[c] for c in COLUMNS[:10]), m.partition(), m.offset()])
            client.insert("trips", rows, column_names=COLUMNS)
            consumer.commit(asynchronous=False)  # only after ClickHouse has the rows
            written += len(rows)
            log.info("wrote %d rows (%d total)", len(rows), written)
    finally:
        consumer.close()
    return written
