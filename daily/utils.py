from __future__ import annotations

import requests

from shared.utils import get_logger

logger = get_logger('borg_daily')


def hc_ping(url: str, data: str | None = None):
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Healthcheck failed: {e}')
