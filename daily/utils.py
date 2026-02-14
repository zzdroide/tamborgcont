from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Thread

import requests

from shared.utils import LoggerPurpose, get_logger

logger = get_logger('borg_daily', LoggerPurpose.DAILY)


def hc_ping(url: str, data: str | None = None):
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Healthcheck failed: {e}')


class JoinRaiseThread(Thread, ABC):
    def __init__(self, name, logger):
        super().__init__(name=name)
        self.logger = logger
        self.exception: Exception | None = None

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.logger.exception('')
            self.exception = e

    @abstractmethod
    def _run(self):
        pass

    def join_raise(self, timeout=None):
        self.join(timeout)
        if self.exception:
            raise self.exception
