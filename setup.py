#!/usr/bin/env python

from setuptools import setup
import os
import config


if __name__ == "__main__":
    basedir = os.path.join(os.path.expanduser('~'),'RAGU')
    if not os.path.isdir(basedir):
        os.mkdir(basedir)
    if not os.path.isfile(basedir+'/config.ini'):
        config.create_config(basedir+'/config.ini')

    # call setup
    setup()