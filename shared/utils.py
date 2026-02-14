from __future__ import annotations

import logging
import os
import sys
from enum import Enum

from systemd import journal
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


class LoggerPurpose(Enum):
    HOOK = 'hook'
    DAILY = 'daily'


def get_logger(name: str, purpose: LoggerPurpose):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent propagation to root logger to avoid duplicate output

    match purpose:
        case LoggerPurpose.HOOK:
            stderr_level = logging.WARNING
        case LoggerPurpose.DAILY:
            if os.getenv('IS_SYSTEMD') == '1':
                # Already logging to systemd journal. Stderr logs are just duplicate spam.
                stderr_level = logging.CRITICAL
            else:
                stderr_level = logging.DEBUG

    # Only add handlers if they don't already exist
    if len(logger.handlers) == 0:
        journal_handler = journal.JournalHandler(SYSLOG_IDENTIFIER=name)
        journal_handler.setLevel(logging.DEBUG)
        logger.addHandler(journal_handler)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(stderr_level)
        logger.addHandler(stderr_handler)

    return logger


@retry(
    retry=retry_if_exception_type(FileExistsError),
    wait=wait_fixed(1),
    stop=stop_after_attempt(4),
    reraise=True,
)
def mkdir_lock(paths):
    """
    When two ssh commands are executed consecutively,
    the first close_session is executed about 0.5s after the second open_session.
    So retry for 3s so the late hook can finish releasing.
    """
    paths.lock.mkdir()
