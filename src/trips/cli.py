"""`trips run data/*.csv`: send the files through Kafka into ClickHouse and report what happened."""

from __future__ import annotations

import argparse
import logging
import sys

from trips import pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trips", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("run", "ingest the files, then sink everything into ClickHouse"),
        ("ingest", "only send the files to Kafka"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("files", nargs="+", help="CSV files with the trips header")
    sub.add_parser("sink", help="only move what is in Kafka into ClickHouse")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("trips")

    if args.command in ("run", "ingest"):
        report = pipeline.ingest(args.files)
        log.info(
            "ingest: %d sent, %d delivered, %d failed, %d rejected",
            report.sent,
            report.delivered,
            report.failed,
            len(report.rejected),
        )
        if report.failed:
            return 1
    if args.command in ("run", "sink"):
        log.info("sink: %d rows written to ClickHouse", pipeline.sink())
    return 0


if __name__ == "__main__":
    sys.exit(main())
