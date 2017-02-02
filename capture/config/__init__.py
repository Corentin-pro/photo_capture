#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This is setting file."""

import os
import sys
from distutils.util import strtobool

from utils.console_color import ConsoleColor


class Config(object):
    """Config makes configuration."""

    # paths
    STORAGE_DIR = 'storage'
    STATIC_DIR = 'static'
    PHOTOS_DIR = STATIC_DIR + '/photos'
    LOGS_DIR = STORAGE_DIR + '/logs'

    # for flask default
    DEBUG = bool(strtobool(os.getenv('DEBUG', 'true')))
    PORT = int(os.getenv('PORT'))
    SECRET_KEY = "\xcf\xf7J/\xa4\xb1/\xe1\xc17\xbe\x04\xc1\x0bb2Y\x02\x10O5\xd2\xe0\x91d"

    # generating madatory directories
    def generate_directories(self):
        """Create directories declared in this Config class"""
        for config_attribute_name in dir(self):
            if "__" not in config_attribute_name and config_attribute_name.endswith("_DIR"):
                path = getattr(self, config_attribute_name)
                if not os.path.exists(path):
                    if __debug__:
                        print ConsoleColor.GREEN + "[INFO]" + ConsoleColor.ENDCOLOR + " Creating path : " + path
                    os.makedirs(path)
        sys.stdout.flush()
