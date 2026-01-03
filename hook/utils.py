from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException


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
        [arc for arc in arcs if arc[1] != f'{user}(temp)']
    )


class BadRepoError(Exception):
    pass


session = requests.Session()
adapter = HTTPAdapter(max_retries=0)
session.mount('http://', adapter)


def get_waiting_for(repo: str):
    """Just a convenience. Not for security because http server can be trivially DoSed."""
    try:
        r = session.get(f'http://127.0.0.1:8087/{repo}', timeout=1)
        r.raise_for_status()
        r.encoding = 'utf-8'
        return r.text.strip()
    except RequestException:
        return None
