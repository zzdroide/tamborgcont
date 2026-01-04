from __future__ import annotations

import logging
import sys

from systemd import journal
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def get_logger(name: str | None, syslog_identifier: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Prevent propagation to root logger to avoid duplicate output

    # Only add handlers if they don't already exist
    if len(logger.handlers) == 0:
        journal_handler = journal.JournalHandler(SYSLOG_IDENTIFIER=syslog_identifier)
        journal_handler.setLevel(logging.INFO)
        logger.addHandler(journal_handler)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
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
