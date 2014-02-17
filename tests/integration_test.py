
import unittest
import docker
import os

from docker_container_runner import utils
from docker_container_runner.manager import Application, DockerDaemon, Hipache
from docker import APIError


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):

        print """
        Setting up
        """

        os.environ['REGISTRY_USER'] = "dcrtest"
        os.environ['REGISTRY_PASS'] = "1secretpassword"
        os.environ['REGISTRY_EMAIL'] = "thatcher+dcr@docker.com"
        os.environ['ENV_VAR1'] = "One"

        self.domain = "dcr-test.blue3.koffiedik.net"

        directives = utils.read_appconfig("test_application.yml")
        release_name = directives['test_application']['release_name']

        name, config = directives.items()[0]

        # Create the application
        settings = utils.read_settings('settings.yml')
        application = Application(release_name, config, settings)
        self.application = application

        # get (unitialized) containers
        self.containers = application.get_containers()

        # stop and remove container if it exists
        self.application.stop_containers()
        self.application.remove_containers()

        print """
        Setting up done
        """

    def tearDown(self):
        print """
        tearing down
        """

        try:
            self.application.stop_containers()
            self.application.remove_containers()
        except docker.APIError:
            pass

        print """
        tearing down complete
        """


#########################
##  INFORMATION TESTS  ##
#########################


class TestGetStatus(BaseTestCase):
    def runTest(self):
        res = self.application.get_status()

        acceptedValues = ['stopped', 'running', 'doesnotexist']
        for status in res:
            self.assertIn(status, acceptedValues)


class TestRunningStatus(BaseTestCase):
    def runTest(self):
        self.application.create_containers()
        create_results = self.application.start_containers()
        res = self.application.get_status()

        acceptedValues = ['stopped', 'running', 'doesnotexist']
        for status in res:
            self.assertIn(status, acceptedValues)


class TestPullContainer(BaseTestCase):
    def runTest(self):
        login = self.application.login_registry()
        results = self.application.pull_image()
        for result in results:
            self.assertNotIn("Authentication is required", result)
            self.assertNotIsInstance(result, APIError)

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


class TestLoginToRegistry(BaseTestCase):

    def runTest(self):
        results = self.application.login_registry()

        for result in results:
            self.assertEqual('Login Succeeded', result[u'Status'])


class TestRegisterContainer(BaseTestCase):

    def runTest(self):
        self.application.create_containers()
        self.application.start_containers()
        result = self.application.register(self.domain)

        print result


class TestUnregisterContainer(BaseTestCase):

    def runTest(self):
        self.application.create_containers()
        self.application.start_containers()
        self.application.register(self.domain)
        result = self.application.unregister(self.domain)

        print result


class TestRedisStatus(BaseTestCase):
    def runTest(self):
        result = self.application.redis_status(self.domain)

        print result


class TestStartLinkedContainer(BaseTestCase):
    def runTest(self):
        # Create the application
        settings = utils.read_settings('settings.yml')

        directives = utils.read_appconfig("child_application.yml")

        name, config = directives.items()[0]

        release_name = config['release_name']
        child_application = Application(release_name, config, settings)
        child_application.containers = child_application.get_containers()

        # check if we have instantiated container objects
        self.assertNotEquals(len(child_application.containers), 0)

        # create the 'parent' container
        self.application.create_containers()
        self.application.start_containers()
        self.application.get_status()

        # clean
        child_application.stop_containers()
        child_application.remove_containers()

        # create child
        child_application.pull_image()
        child_application.create_containers()
        child_application.start_containers()
        child_application_details = child_application.get_details()
        print child_application_details

        for detail in child_application_details:
            self.assertEqual(detail[u'State'][u'Running'], True)

        self.application.get_status()

        # clean again
        child_application.stop_containers()
        child_application.remove_containers()

        print child_application

