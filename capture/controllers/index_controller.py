#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This is top_controller file"""


from flask import render_template

from config import Config


def show():
    """
    Index page
    """
    return render_template('index.html')
