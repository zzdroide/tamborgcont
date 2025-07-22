from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def getidx(lst, index, default=None):
    try:
        return lst[index]
    except IndexError:
        return default


def mkfile(path: Path):
    path.open('x').close()


def arcs2str(arcs: list):
    lines = (f'{arc[0]}\x00{arc[1]}' for arc in arcs)
    return '\x00'.join(lines) + '\x00'


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
