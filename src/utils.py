def getidx(list, index, default=None):
    try:
        return list[index]
    except IndexError:
        return default


def mkfile(file_path):
    open(file_path, 'x').close()
