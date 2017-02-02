#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This is app main file."""


# Python 3 compatibility
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from logging import handlers, StreamHandler
import logging
import subprocess

from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

from config import Config
from controllers import index_controller
from utils.colored_formatter import ColoredFormatter


class PhotoCapture(object):
    """Application class"""

    app = Flask(__name__)
    app.config.from_object('config.Config')

    CORS(app)  # cross domain でアクセス可能にする

    # Easy global variable to keep track of the capturing process
    capture_process = None
    photo_process = None
    logger = logging.getLogger("capture")

    # ========== Routing ==========

    @staticmethod
    @app.route('/', methods=('GET', 'POST'))
    def index():
        """Index page"""
        return index_controller.show()

    # ========== API ==========

    @staticmethod
    @app.route('/api/start_capture', methods=['POST'])
    def start_capture():
        """Retrieves photos info"""

        return_status = "error"
        return_message = "Unknown error"
        # Check no process is running
        if PhotoCapture.capture_process is None or PhotoCapture.capture_process.returncode is not None:

            # Killing the photo process before starting a new capture
            if PhotoCapture.photo_process is not None:
                if PhotoCapture.photo_process.returncode is None:
                    PhotoCapture.photo_process.kill()
                    PhotoCapture.photo_process = None

            PhotoCapture.logger.info("Starting the capture")
            # Max 1 min
            command = "ffmpeg -y -f v4l2 -t 00:01:00 -i /dev/video0 " + os.path.join(Config.PHOTOS_DIR, "output.mp4")
            PhotoCapture.capture_process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)

            # Cleaning previous photos
            subprocess.call("rm " + Config.PHOTOS_DIR + "/*.jpg", shell=True)
            return_status = "ok"
            return_message = "Capture started"
        else:
            return_message = "Cannot start a capture while previous one is running"
            PhotoCapture.logger.info(return_message)

        return jsonify(status=return_status, message=return_message)

    @staticmethod
    @app.route('/api/stop_capture', methods=['POST'])
    def stop_capture():
        """Retrieves photos info"""

        return_status = "error"
        return_message = "Unknown error"
        # Kill previous capture process and process the video
        if PhotoCapture.capture_process is not None:
            if PhotoCapture.capture_process.returncode is None:
                PhotoCapture.logger.info("Stoping the capture")
                PhotoCapture.capture_process.communicate("q")
            capture_return_code = PhotoCapture.capture_process.wait()
            PhotoCapture.logger.info("Capture ended with code : %d", capture_return_code)
            PhotoCapture.capture_process = None

            command = "ffmpeg -i "\
                + os.path.join(Config.PHOTOS_DIR, "output.mp4")\
                + " -r 1 -f image2 -v warning -y "\
                + os.path.join(Config.PHOTOS_DIR, "photo%3d.jpg")

            # Killing the photo process before starting a new one
            if PhotoCapture.photo_process is not None:
                if PhotoCapture.photo_process.returncode is None:
                    PhotoCapture.photo_process.kill()
                    PhotoCapture.photo_process = None
            PhotoCapture.photo_process = subprocess.Popen(command, shell=True)
            return_status = "ok"
            return_message = "Capture stoped"
        else:
            return_message = "No capture to stop"
            PhotoCapture.logger.info(return_message)

        return jsonify(status=return_status, message=return_message)

    @staticmethod
    @app.route('/api/refresh', methods=['POST'])
    def photos():
        """Retrieves photos info"""

        # Waiting for the photo process to finish
        if PhotoCapture.photo_process is not None:
            PhotoCapture.photo_process.wait()

        photo_list = []
        file_list = sorted(os.listdir(Config.PHOTOS_DIR))
        for file_name in file_list:
            if file_name.endswith(".jpg"):
                photo_list.append({"path": os.path.join(Config.PHOTOS_DIR, file_name), "name": file_name})
        return jsonify(status="ok", message=photo_list)

    @staticmethod
    @app.route('/api/download', methods=['POST'])
    def download():
        """Retrieves photos info"""
        import zipfile

        photo_list = request.form.getlist('photos[]')

        # Generating the zip
        zip_filename = 'output.zip'
        zip_path = os.path.join(Config.PHOTOS_DIR, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipfile:
            counter = 0
            for file_name in photo_list:
                zipfile.write(os.path.join(Config.PHOTOS_DIR, file_name), "photo%d.jpg" % counter)
                counter += 1
        return redirect(zip_path)

    @staticmethod
    @app.route('/api/upload', methods=['POST'])
    def upload():
        """Upload video"""

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
            if PhotoCapture.photo_process is not None:
                if PhotoCapture.photo_process.returncode is None:
                    PhotoCapture.photo_process.kill()
                    PhotoCapture.photo_process = None
            PhotoCapture.photo_process = subprocess.Popen(command, shell=True)

        return redirect("/")

    # ==============================

    @staticmethod
    def start():
        """Start the application"""

        # generate directories declared in Config if non existant
        Config().generate_directories()

        # Adding a (rotating) file handler to the logging system : outputing in capture.log
        PhotoCapture.logger.setLevel(logging.DEBUG)
        file_log_handler = handlers.RotatingFileHandler(
            os.path.join(Config.LOGS_DIR, "capture.log"),
            maxBytes=500000,
            backupCount=5)
        file_log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s %(levelname)s : %(message)s')
        file_log_handler.setFormatter(log_formatter)
        PhotoCapture.logger.addHandler(file_log_handler)
        # Adding the file handler to Flask
        PhotoCapture.app.logger.addHandler(file_log_handler)
        # Adding the file handler to werkzeug (HTTP requests)
        http_logger = logging.getLogger('werkzeug')
        http_logger.addHandler(file_log_handler)

        if __debug__:
            # Adding an handler to the logging system (default has none) : outputing in stdout
            terminal_log_handler = StreamHandler(sys.stdout)
            terminal_log_handler.setLevel(logging.DEBUG)
            colored_log_formatter = ColoredFormatter('%(asctime)s %(levelname)s : %(message)s')
            terminal_log_handler.setFormatter(colored_log_formatter)
            PhotoCapture.logger.addHandler(terminal_log_handler)

        PhotoCapture.app.run(
            debug=PhotoCapture.app.config['DEBUG'],
            host='0.0.0.0',
            port=PhotoCapture.app.config['PORT'],
            threaded=False)


if __name__ == '__main__':
    PhotoCapture.start()
