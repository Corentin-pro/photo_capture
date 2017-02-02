#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This is app main file."""


import os
import sys
import logging
import subprocess
from logging import handlers, StreamHandler

from werkzeug.security import gen_salt
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

from config import Config
from controllers import index_controller
from utils.colored_formatter import ColoredFormatter


APPLICATION = Flask(__name__)
APPLICATION.config.from_object('config.Config')

CORS(APPLICATION)  # cross domain でアクセス可能にする

# Easy global variable to keep track of the capturing process
capture_process = None
photo_process = None
CAPTURE_LOGGER = logging.getLogger("capture")


# ========== Routing ==========


@APPLICATION.route('/', methods=('GET', 'POST'))
def index():
    """Index page"""
    return index_controller.show()

# ========== API ==========


@APPLICATION.route('/api/start_capture', methods=['POST'])
def start_capture():
    """Retrieves photos info"""
    global capture_process, photo_process, CAPTURE_LOGGER

    return_status = "error"
    return_message = "Unknown error"
    # Check no process is running
    if capture_process is None or capture_process.returncode is not None:

        # Killing the photo process before starting a new capture
        if photo_process is not None:
            if photo_process.returncode is None:
                photo_process.kill()
                photo_process = None

        CAPTURE_LOGGER.info("Starting the capture")
        # Max 1 min
        command = "ffmpeg -y -f v4l2 -t 00:01:00 -i /dev/video0 " + os.path.join(Config.PHOTOS_DIR, "output.mp4")
        capture_process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)

        # Cleaning previous photos
        subprocess.call("rm " + Config.PHOTOS_DIR + "/*.jpg", shell=True)
        return_status = "ok"
        return_message = "Capture started"
    else:
        return_message = "Cannot start a capture while previous one is running"
        CAPTURE_LOGGER.info(return_message)

    return jsonify(status=return_status, message=return_message)


@APPLICATION.route('/api/stop_capture', methods=['POST'])
def stop_capture():
    """Retrieves photos info"""
    global capture_process, photo_process, CAPTURE_LOGGER

    return_status = "error"
    return_message = "Unknown error"
    # Kill previous capture process and process the video
    if capture_process is not None:
        if capture_process.returncode is None:
            CAPTURE_LOGGER.info("Stoping the capture")
            capture_process.communicate("q")
        capture_return_code = capture_process.wait()
        CAPTURE_LOGGER.info("Capture ended with code : %d", capture_return_code)
        capture_process = None

        command = "ffmpeg -i "\
                  + os.path.join(Config.PHOTOS_DIR, "output.mp4")\
                  + " -r 1 -f image2 -v warning -y "\
                  + os.path.join(Config.PHOTOS_DIR, "photo%3d.jpg")

        # Killing the photo process before starting a new one
        if photo_process is not None:
            if photo_process.returncode is None:
                photo_process.kill()
                photo_process = None
        photo_process = subprocess.Popen(command, shell=True)
        return_status = "ok"
        return_message = "Capture stoped"
    else:
        return_message = "No capture to stop"
        CAPTURE_LOGGER.info(return_message)

    return jsonify(status=return_status, message=return_message)


@APPLICATION.route('/api/refresh', methods=['POST'])
def photos():
    """Retrieves photos info"""
    global photo_process

    # Waiting for the photo process to finish
    if photo_process is not None:
        photo_process.wait()

    photo_list = []
    file_list = sorted(os.listdir(Config.PHOTOS_DIR))
    for file_name in file_list:
        if file_name.endswith(".jpg"):
            photo_list.append({"path": os.path.join(Config.PHOTOS_DIR, file_name), "name": file_name})
    return jsonify(status="ok", message=photo_list)


@APPLICATION.route('/api/download', methods=['POST'])
def download():
    """Retrieves photos info"""
    global CAPTURE_LOGGER
    import zipfile

    photo_list = request.form.getlist('photos[]')

    # Generating the zip
    zip_filename = 'output.zip'
    zip_path = os.path.join(Config.PHOTOS_DIR, zip_filename)
    CAPTURE_LOGGER.info(zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipfile:
        counter = 0
        for file_name in photo_list:
            zipfile.write(os.path.join(Config.PHOTOS_DIR, file_name), "photo%d.jpg" % counter)
            counter += 1
    return redirect(zip_path)


@APPLICATION.route('/api/upload', methods=['POST'])
def upload():
    """Upload video"""
    global photo_process, CAPTURE_LOGGER
    CAPTURE_LOGGER.info(request.files)
    movie_file = request.files['movie']
    if movie_file:
        movie_file.save(os.path.join(Config.PHOTOS_DIR, "output.mp4"))

        # Cleaning previous photos
        subprocess.call("rm " + Config.PHOTOS_DIR + "/*.jpg", shell=True)

        command = "ffmpeg -i "\
                + os.path.join(Config.PHOTOS_DIR, "output.mp4")\
                + " -r 1 -f image2 -v warning -y "\
                + os.path.join(Config.PHOTOS_DIR, "photo%3d.jpg")

        # Killing the photo process before starting a new one
        if photo_process is not None:
            if photo_process.returncode is None:
                photo_process.kill()
                photo_process = None
        photo_process = subprocess.Popen(command, shell=True)

    return redirect("/")

# ==============================


if __name__ == '__main__':
    # generate directories declared in Config if non existant
    Config().generate_directories()

    # Adding a (rotating) file handler to the logging system : outputing in capture.log
    CAPTURE_LOGGER.setLevel(logging.DEBUG)
    FILE_LOG_HANDLER = logging.handlers.RotatingFileHandler(os.path.join(Config.LOGS_DIR, "capture.log"),
                                                            maxBytes=500000,
                                                            backupCount=5)
    FILE_LOG_HANDLER.setLevel(logging.DEBUG)
    FORMATTER = logging.Formatter('%(asctime)s %(levelname)s : %(message)s')
    FILE_LOG_HANDLER.setFormatter(FORMATTER)
    CAPTURE_LOGGER.addHandler(FILE_LOG_HANDLER)
    # Adding the file handler to Flask
    APPLICATION.logger.addHandler(FILE_LOG_HANDLER)
    # Adding the file handler to werkzeug (HTTP requests)
    HTTP_LOGGER = logging.getLogger('werkzeug')
    HTTP_LOGGER.addHandler(FILE_LOG_HANDLER)

    if __debug__:
        # Adding an handler to the logging system (default has none) : outputing in stdout
        TERMINAL_LOG_HANDLER = StreamHandler(sys.stdout)
        TERMINAL_LOG_HANDLER.setLevel(logging.DEBUG)
        COLORED_FORMATTER = ColoredFormatter('%(asctime)s %(levelname)s : %(message)s')
        TERMINAL_LOG_HANDLER.setFormatter(COLORED_FORMATTER)
        CAPTURE_LOGGER.addHandler(TERMINAL_LOG_HANDLER)

    APPLICATION.run(debug=APPLICATION.config['DEBUG'],
                    host='0.0.0.0',
                    port=APPLICATION.config['PORT'],
                    threaded=False)
