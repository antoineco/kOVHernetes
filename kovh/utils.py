def columns(headers, data):
    """Format input into columns

    Arguments:
    headers -- list or tuple of header strings
    data -- list of data tuples
    """
    # add headers to data set
    data.insert(0, headers)

    # populate column sizes
    col_size = []
    for d in data:
        for i, v in enumerate(d):
            try:
                if len(str(v)) > col_size[i]:
                    col_size[i] = len(v)
            except IndexError:
                col_size.append(len(v))

    # generate format strings
    fmt = []
    for width in col_size:
        fmt.append('{{:<{}}}'.format(width))

    # populate formatted lines
    lines = []
    for d in data:
        lines.append('  '.join(fmt[:len(d)]).format(*d))

    return '\n'.join(lines)
