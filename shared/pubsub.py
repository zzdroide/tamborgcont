"""
A simple pubsub with pipes, for a single subscriber only.
"""
from __future__ import annotations

import contextlib
import os
import select
import time
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .constants import Paths


class PubSub(Thread):
    def __init__(self, paths: Paths):
        super().__init__(daemon=True, name=str(paths.pubsub))
        self.paths = paths
        self.sub_queue = Queue[str]()

        with contextlib.suppress(FileExistsError):
            os.mkfifo(self.paths.pubsub)

    def publish(self, message: str):
        try:
            fd = os.open(self.paths.pubsub, os.O_WRONLY | os.O_NONBLOCK)
            with os.fdopen(fd, 'w') as pipe:
                pipe.write(message + '\n')
        except OSError:
            # No subscriber
            pass

    def run(self):
        with self.paths.pubsub.open('r') as pipe:
            while True:
                rlist, _, _ = select.select([pipe], [], [])
                if not rlist:
                    return False
                line = pipe.readline().strip()
                self.sub_queue.put(line)

    def wait_for(
        self,
        *,
        prefix: str | None = None,
        match: str | None = None,
        timeout: float = float('inf'),  # in seconds
    ):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                message = self.sub_queue.get(timeout=remaining)
            except Empty:
                return None
            if prefix and message.startswith(prefix):
                return message
            if match and match == message:
                return True
