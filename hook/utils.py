from __future__ import annotations

import logging
import sys

from systemd import journal


def arcs2str(arcs: list):
    lines = (f'{arc[0]}\x00{arc[1]}\x00' for arc in arcs)
    return ''.join(lines)


def arcs2list(dump: str):
    arcs = []
    while dump:
        arc_id, _sep, dump = dump.partition('\x00')
        arc_name, _sep, dump = dump.partition('\x00')
        arcs.append((arc_id, arc_name))
    return arcs


def without_temp(arcs: list | str, user: str):
    if isinstance(arcs, str):
        arcs = arcs2list(arcs)
    return arcs2str(
        [arc for arc in arcs if arc[1] != f'{user}[temp]']
    )


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    journal_handler = journal.JournalHandler(SYSLOG_IDENTIFIER='borg_ssh_hook')
    journal_handler.setLevel(logging.INFO)
    logger.addHandler(journal_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    logger.addHandler(stderr_handler)

    return logger


class BadRepoError(Exception):
    pass
