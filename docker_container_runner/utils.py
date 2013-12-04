import yaml


def read_appconfig(filename):
    print filename

    try:
        stream = open(filename)
    except IOError as err:
        print "no filename given, or incorrect file"
        return err

    config = yaml.load(stream)

    directives = {}

    for key, values in config.items():
        directives[key] = {}

        print "processing {}".format(key)

        # simple directives
        directives[key]['container'] = values.get("container", None)
        directives[key]['image'] = values.get("image", None)
        directives[key]['command'] = values.get("command", None)
        directives[key]['hostname'] = values.get("hostname", None)
        directives[key]['dep_env'] = values.get("dep_env", None)
        directives[key]['env'] = values.get("env", None)

        # more complex ones

        # PORTS
        ports = values.get("ports", None)

        c_ports = {}  # ports for create, needs an empty obj
        s_ports = {}  # ports for start, has the 'other side'

        for port in ports or []:
            parts = port.split(":")

            host_ip = ''
            host_port = ''

            if len(parts) == 1:
                container_port = parts[0]
            if len(parts) == 2:
                host_port = parts[0]
                container_port = parts[1]
            if len(parts) == 3:
                host_ip = parts[0]
                host_port = parts[1]
                container_port = parts[2]

            if not (container_port.endswith('tcp') or container_port.endswith('udp')):
                container_port += "/tcp"

            c_ports[container_port] = {}
            s_ports[container_port] = [{'HostIp': host_ip, 'HostPort': host_port}]

        print "s_ports = ", s_ports

        directives[key]['c_ports'] = c_ports
        directives[key]['s_ports'] = s_ports

        # VOLUMES
        volumes = values.get("volumes", None)

        vols = {}
        binds = {}
        for volume in volumes or []:
            parts = volume.split(":")
            # host mount (e.g. /mnt:/tmp, bind mounts host's /tmp to /mnt in the container)
            if len(parts) == 2:
                vols[parts[1]] = {}
                binds[parts[0]] = parts[1]
                # docker mount (e.g. /www, mounts a docker volume /www on the container at the same location)
            else:
                vols[parts[0]] = {}

        print 'volumes = ', vols

        directives[key]['vols'] = vols
        directives[key]['binds'] = binds

    return directives


def read_settings(filename):
    print filename

    try:
        stream = open(filename)
    except IOError as err:
        print "no filename given, or incorrect file"
        return err

    config = yaml.load(stream)

    # return yaml.load(stream)
    #
    # directives = {}
    #
    # for key, values in config.items():
    #     directives[key] = {}
    #
    #     print "processing {}".format(key)
    #
    #     directives[key]['base_domains'] = values.get("base_domains", None)[0]
    #     directives[key]['hipaches'] = values.get("hipaches", None)
    #     directives[key]['daemons'] = values.get("daemons", None)
    #

    return config

