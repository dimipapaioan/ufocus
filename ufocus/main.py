# -*- coding: utf-8 -*-

import logging.config

from logging_config import LOGGING_CONFIG
from main_window import main

logging.config.dictConfig(LOGGING_CONFIG)


def run_main() -> int:
    exit_code: int = main()
    return exit_code


if __name__ == "__main__":
    import sys

    exit_code = main()
    sys.exit(exit_code)
