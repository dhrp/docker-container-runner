
import unittest
import docker

from docker_container_runner import utils
from docker_container_runner.manager import Application, DockerDaemon, Hipache



class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):

        directives = utils.read_appconfig("test_application.yml")
        name, config = directives.items()[0]

        release_name = config['release_name']

        # Create the application
        settings = utils.read_settings('test_settings.yml')
        application = Application(release_name, config, settings)
        self.application = application

        # get (unitialized) containers
        self.containers = application.get_containers()

        # stop and remove container if it exists
        self.application.stop_containers()
        self.application.remove_containers()

    def tearDown(self):
        try:
            self.application.stop_containers()
            self.application.remove_containers()
        except docker.APIError:
            pass

#########################
##  INFORMATION TESTS  ##
#########################


class TestGetStatus(BaseTestCase):
    def runTest(self):
        res = self.application.get_status()

        acceptedValues = ['stopped', 'running', 'doesnotexist']
        for status in res:
            self.assertIn(status, acceptedValues)


class TestPullContainer(BaseTestCase):
    def runTest(self):
        results = self.application.pull_image()

        self.assertEqual(None, results)

#
# class TestRemoveContainer(BaseTestCase):
#     def runTest(self):
#         results = self.application.remove_containers()
#
#         for result in results:
#             print result
#             # returns 0 if succesfull, 1 if it fails
#             self.assertEqual(None, result)


class TestCreateContainer(BaseTestCase):
    def runTest(self):
        create_results = self.application.create_containers()

        for result in create_results:
            print result
            # returns None if succesfull, 1 if it fails
            self.assertEqual(None, result)


class TestStartContainer(BaseTestCase):
    def runTest(self):

        self.application.create_containers()
        create_results = self.application.start_containers()
        containers_details = self.application.get_details()

        for result in create_results:
            print result
            # returns None if succesfull, 1 if it fails
            self.assertEqual(None, result)

        for details in containers_details:
            print details

            self.assertTrue(details[u'State'][u'Running'])

            # ports
            self.assertEqual(details[u'NetworkSettings'][u'Ports'][u'81/tcp'][0]['HostIp'], '0.0.0.0')
            self.assertEqual(details[u'NetworkSettings'][u'Ports'][u'81/tcp'][0]['HostPort'], '81')

            # volumes
            self.assertIn('/var/lib/docker/', details[u'Volumes'][u'testdir'])
            self.assertIn('/tmp', details[u'Volumes'][u'testdir2'])

            # env
            self.assertIn('ENV_VAR1=One', details[u'Config'][u'Env'][0])
