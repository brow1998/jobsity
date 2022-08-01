"""
    This module contains all multithreading related functions.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Union


def run_task(function: Callable, items: Union[list, tuple], max_threads: int = 32, *args, **kwargs) -> list:
    """
        Receive a :function (Python callable), a list of :items
        and split each item into a thread to be executed in parallel.

        Any *args and **kwargs will be passed as-is to the function executor.

        More info about multi-threading in Python can be found here:
        https://docs.python.org/3/library/concurrent.futures.html
    """
    num_workers = min(len(items), max_threads) if len(items) > 0 else 1
    processed_items = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_items = [executor.submit(
            function, item, *args, **kwargs) for item in items]

        for future in concurrent.futures.as_completed(future_items):
            processed_items.append(future.result())

    return processed_items
    