#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Formatter changing logger's record levelname to have colors in the console"""


import logging

from utils.console_color import ConsoleColor


class ColoredFormatter(logging.Formatter):
    """Formatter changing the record during format : adds colors to levelname"""
    def format(self, record):
        levelno = record.levelno
        if logging.ERROR == levelno:
            levelname_color = ConsoleColor.RED + "[" + record.levelname + "]" + ConsoleColor.ENDCOLOR
        elif logging.WARNING == levelno:
            levelname_color = ConsoleColor.ORANGE + "[" + record.levelname + "]" + ConsoleColor.ENDCOLOR
        elif logging.INFO == levelno:
            levelname_color = ConsoleColor.GREEN + "[" + record.levelname + "]" + ConsoleColor.ENDCOLOR
        elif logging.DEBUG == levelno:
            levelname_color = ConsoleColor.BLUE + "[" + record.levelname + "]" + ConsoleColor.ENDCOLOR
        else:
            levelname_color = "[" + record.levelname + "]"
        record.levelname = levelname_color
        return logging.Formatter.format(self, record)
