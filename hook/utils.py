from pathlib import Path


def getidx(lst, index, default=None):
    try:
        return lst[index]
    except IndexError:
        return default


def mkfile(path: Path):
    path.open('x').close()
