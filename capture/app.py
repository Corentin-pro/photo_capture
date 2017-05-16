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
import threading
import time

from flask import Flask, jsonify, redirect, request
import pygame
import pygame.camera

from config import Config
from controllers import index_controller
from utils.colored_formatter import ColoredFormatter


class PhotoCapture(object):
    """Application class"""

    app = Flask(__name__)
    app.config.from_object('config.Config')

    logger = logging.getLogger("capture")

    video_process = None

    capture_on = False

    @staticmethod
    def capture_photo(fps):
        """
        This function takes pictures from the camera.
        It is meant to be threaded and started/stopped changing the class variable capture_on.
        (capture_on should be True before before starting this function)
        """
        pygame.camera.init()
        cam = pygame.camera.Camera("/dev/video0", (1024, 768))
        cam.start()
        PhotoCapture.logger.info("Capture start")
        photo_iterator = 1
        while PhotoCapture.capture_on:
            pygame.image.save(
                cam.get_image(),
                os.path.join(Config.PHOTOS_DIR, "photo{:0>2d}.jpg".format(photo_iterator)))
            photo_iterator += 1
            time.sleep(1/fps)
            if photo_iterator > 999:
                PhotoCapture.capture_on = False
        cam.stop()
        PhotoCapture.logger.info("Capture stop")

    # ========== Routing ==========

    @staticmethod
    @app.route('/', methods=('GET', 'POST'))
    def index():
        """Index page"""
        return index_controller.show()

    # ========== API ==========

    @staticmethod
    @app.route('/api/start_capture/<int:fps>', methods=['POST'])
    def start_capture(fps):
        """Retrieves photos info"""

        return_status = "error"
        return_message = "Unknown error"

        # Hard limit on fps at 30
        if fps > 30:
            fps = 30
        # Check no process is running
        if not PhotoCapture.capture_on:
            # Cleaning previous photos
            subprocess.call("rm " + Config.PHOTOS_DIR + "/*.jpg", shell=True)

            PhotoCapture.capture_on = True
            PhotoCapture.logger.info("Starting the capture")
            capture_thread = threading.Thread(target=PhotoCapture.capture_photo, args=(fps,))
            capture_thread.start()
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
        # PhotoCapture.logger.info("Threads :")
        # PhotoCapture.logger.info(threading.enumerate())
        # Kill previous capture process and process the video
        if PhotoCapture.capture_on:
            PhotoCapture.capture_on = False
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

        photo_list = []
        file_list = sorted(os.listdir(Config.PHOTOS_DIR))
        for file_name in file_list:
            if file_name.endswith(".jpg"):
                photo_list.append({"path": os.path.join(Config.PHOTOS_DIR, file_name), "name": file_name})
        return jsonify(status="ok", message=photo_list)

    @staticmethod
    @app.route('/api/refresh/<int:offset>', methods=['POST'])
    def photos_offseted(offset):
        """Retrieves photos info (with offset)"""

        photo_list = []
        file_list = sorted(os.listdir(Config.PHOTOS_DIR))
        if offset < len(file_list):
            file_list = file_list[offset:]
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
    @app.route('/api/upload/<int:fps>', methods=['POST'])
    def upload(fps):
        """Upload video"""

        movie_file = request.files['movie']
        if movie_file:

            # Killing previous video process
            if PhotoCapture.video_process:
                if not PhotoCapture.video_process.returncode:
                    PhotoCapture.logger.info("Stopping previous process")
                    # Killing all the ffmep processes/subprocesses
                    subprocess.call("kill -9 $(pidof ffmpeg)", shell=True)
                PhotoCapture.video_process = None

            movie_file.save(os.path.join(Config.PHOTOS_DIR, "output.mp4"))

            # Cleaning previous photos
            subprocess.call("rm " + Config.PHOTOS_DIR + "/*.jpg", shell=True)

            command = "ffmpeg -i %s  -r %d -f image2 -v warning -y %s" %\
                (os.path.join(Config.PHOTOS_DIR, "output.mp4"),
                 fps,
                 os.path.join(Config.PHOTOS_DIR, "photo%3d.jpg"))

            PhotoCapture.video_process = subprocess.Popen(command, shell=True)

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
            threaded=True)


if __name__ == '__main__':
    PhotoCapture.start()
