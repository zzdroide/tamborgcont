def getidx(list, index, default=None):
    try:
        return list[index]
    except IndexError:
        return default
