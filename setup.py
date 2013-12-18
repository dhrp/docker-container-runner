#!/usr/bin/env python

from setuptools import setup

setup(name='dcr',
      version='0.1.5',
      description='Docker Container Runner - start Docker Containers from YML',
      url='http://github.com/dhrp/docker-runner',
      author='Thatcher Peskens',
      author_email='thatcher@docker.com',
      license='MIT',
      scripts=['dcr'],
      packages=['docker_container_runner'],
      install_requires=[
          'docker-py==0.2.3',
          'simplejson',
          'jsonpath_rw',
          'pyyaml',
          'redis',
          'bgtunnel'
      ],
      dependency_links=[
          'https://github.com/dotcloud/docker-py/archive/0.2.3.tar.gz#egg=docker-py-0.2.3'
      ],
      zip_safe=False)

