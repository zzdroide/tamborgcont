from __future__ import annotations

import logging

import requests

from shared.utils import get_logger

logger = get_logger(name='borg_daily', stderr_level=logging.CRITICAL)


def hc_ping(url: str, data: str | None = None):
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Healthcheck failed: {e}')
