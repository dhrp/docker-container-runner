#!/usr/bin/env python

import yaml 
import docker 
import redis
from jsonpath_rw import jsonpath, parse

d = docker.Client(base_url='unix://var/run/docker.sock', version="1.4")

stream = open("config.yml")
config = yaml.load(stream)
#global result_config
result_config = "configXX"

# :print config

for key, values in config.items():
   #global result_config
   #result_config = "abc"
   print result_config
   print "processing {}".format(key)
   
   image = values.get("image", None)
   command = values.get("command", None)
   volumes = values.get("volumes", None)
   hostname = values.get("hostname", None)
   port = values.get("port", None)
   dep_env = values.get("dep_env", None)
   env = []

   print "found {} {} {}".format(image, command, volumes)

   env_var = None
   if dep_env:
      env_key = dep_env[0].split('=')[0]
      env_value = dep_env[0].split('=')[1]
      env_path = env_value.split('.')
      print env_value
      env_var = ["{}={}".format(env_key, config.get(env_path[0]).get(env_path[1]))]
      #env_item = "{}={}".format(env_key, values.get(env_path[0]).get(env_path[1]).get(env_path[2]))
      #print "dependent environment {}".format(env_item)

   container = d.create_container(image, command, environment=env_var, detach=True)
   
   print container
   result = d.start(container, binds=None)

   details = d.inspect_container(container)
   print details
   # port = details.get("NetworkSettings", None).get("PortMapping", None
   exposed_port = None
   
   exposed_port = details["NetworkSettings"]["PortMapping"]["Tcp"][str(port)]
   print exposed_port
   config['mongodb']['exposed_port'] = exposed_port

print config
#   print config.exposed_port
