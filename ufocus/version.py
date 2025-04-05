version_info = (2, 3, 1)


def get_version() -> str:
    return ".".join(map(str, version_info))
