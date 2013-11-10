# docker-runner

This is an attempt to make my life easier.

It allows you to configure Docker containers in .yaml files and run them with `./runner.py <file>.yml`

runner.py will parse the yml file and use docker-py to create and start the container specified. 
Arguments in yml can be specified with docker commandline like arguments.

**supports**

- image
- ports
- volumes
- environment variables
- cmd

example config:
```
annickspoelstra:
  image: "tea/ghostblog"
  command: ["supervisord","-n"]
  ports: ["6002:22", "127.0.0.1:6001:2368/tcp", "80"]
  volumes: ['/var/sites/annickspoelstra.nl/data/:/data/', '/var/sites/annickspoelstra.nl/files/:/site/']
  env: ["REDIS_HOST=blue1.koffiedik.net", "REDIS_PORT=6379"]
```
