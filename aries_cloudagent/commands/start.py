"""Entrypoint."""

import asyncio
import functools
import logging
import os
import signal
import time
from argparse import ArgumentParser
from typing import Coroutine, Sequence
import cProfile

try:
    import uvloop
except ImportError:
    uvloop = None

from ..core.conductor import Conductor
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.util import common_config

LOGGER = logging.getLogger(__name__)


async def start_app(conductor: Conductor):
    """Start up."""
    await conductor.setup()
    await conductor.start()
    print("Startup Time:", time.time() - global_app_start_time)


async def shutdown_app(conductor: Conductor):
    """Shut down."""
    print("\nShutting down")
    stop_time = time.time()
    await conductor.stop()
    print("App stopping time: ", time.time() - stop_time)


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_START))


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    global global_app_start_time
    global_app_start_time = time.time()
    parser = ArgumentParser()
    parser.prog += " start"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    # thcf
    settings["personal_storage_registered_types"] = {
        "local": "aries_cloudagent.pdstorage_thcf.local.LocalPDS",
        "thcf_data_vault": "aries_cloudagent.pdstorage_thcf.thcf_data_vault.DataVault",
        "own_your_data_data_vault": "aries_cloudagent.pdstorage_thcf.own_your_data_data_vault.OwnYourDataVault",
    }

    # set ledger to read only if explicitely specified
    settings["ledger.read_only"] = settings.get("read_only_ledger", False)

    # Support WEBHOOK_URL environment variable
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        webhook_urls = list(settings.get("admin.webhook_urls") or [])
        webhook_urls.append(webhook_url)
        settings["admin.webhook_urls"] = webhook_urls

    # Create the Conductor instance
    context_builder = DefaultContextBuilder(settings)
    conductor = Conductor(context_builder)

    # Run the application
    if uvloop:
        uvloop.install()
        print("uvloop installed")

    run_loop(start_app(conductor), shutdown_app(conductor))


def run_loop(startup: Coroutine, shutdown: Coroutine):
    """Execute the application, handling signals and ctrl-c."""

    async def init(cleanup):
        """Perform startup, terminating if an exception occurs."""
        try:
            await startup
        except Exception:
            LOGGER.exception("Exception during startup:")
            cleanup()

    async def done():
        """Run shutdown and clean up any outstanding tasks."""
        await shutdown
        tasks = [
            task
            for task in asyncio.Task.all_tasks()
            if task is not asyncio.Task.current_task()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.get_event_loop().stop()

    loop = asyncio.get_event_loop()
    cleanup = functools.partial(asyncio.ensure_future, done(), loop=loop)
    loop.add_signal_handler(signal.SIGTERM, cleanup)
    asyncio.ensure_future(init(cleanup), loop=loop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(done())


if __name__ == "__main__":
    execute()
