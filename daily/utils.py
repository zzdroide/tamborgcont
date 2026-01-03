from __future__ import annotations

import requests

from shared.utils import get_logger

logger = get_logger(None, 'borg_daily')


def hc_ping(url: str, data: str | None = None):
    try:
        requests.post(url, data=data, timeout=10)
    except requests.RequestException as e:
        logger.error(f'Healthcheck failed: {e}')
