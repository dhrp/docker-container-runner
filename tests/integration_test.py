import time
import base64
import io
import os
import signal
import tempfile
import unittest

import docker
import six

import sys

from docker_container_runner import utils
from docker_container_runner.manager import Application, DockerDaemon, Hipache


# FIXME: missing tests for
# export; history; import_image; insert; port; push; tag


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):
        # self.client = docker.Client()
        # self.client.pull('busybox')
        # self.tmp_imgs = []
        # self.tmp_containers = []

        directives = utils.read_appconfig("test_application.yml")
        name, config = directives.items()[0]

        release_name = config['release_name']

        # Create the application
        settings = utils.read_settings('test_settings.yml')
        application = Application(release_name, config, settings)
        self.application = application

        # get (unitialized) containers
        self.containers = application.get_containers()

    def tearDown(self):
        """
        for img in self.tmp_imgs:
            try:
                self.client.remove_image(img)
            except docker.APIError:
                pass
        for container in self.tmp_containers:
            try:
                self.client.stop(container, timeout=1)
                self.client.remove_container(container)
            except docker.APIError:
                pass
        """
        pass

#########################
##  INFORMATION TESTS  ##
#########################


class TestGetStatus(BaseTestCase):
    def runTest(self):
        res = self.application.get_status()

        self.assertIn('doesnotexist', res)


class TestPullContainer(BaseTestCase):
    def runTest(self):
        results = self.application.pull_image()

        self.assertEqual(None, results)


class TestCreateContainer(BaseTestCase):
    def runTest(self):
        create_results = self.application.create_containers()

        for result in create_results:
            # returns 0 if succesfull, 1 if it fails
            self.assertEqual(1, result[0])

