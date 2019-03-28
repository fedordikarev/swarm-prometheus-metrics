#!/usr/bin/env python
""" Collect Prometheus metrics from containers and add labels to them """
from time import sleep

from flask import Flask
from flask import Response

import docker
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

app = Flask(__name__)   #pylint: disable=invalid-name

SELF_DOCKER_ID = None
DOCKER_HOST_NAME = None

def extend_metrics(text, to_extend):
    """ Add extra labels to metrics """
    output = []
    for line in text.splitlines():
        if line.startswith("#"):
            output.append(line)
            continue
        if not line:
            continue
        # print("DEBUG:", line)
        sep = line.rfind(" ")
        (key, value) = (line[:sep], line[sep+1:])
        if key.endswith("}"):
            output.append(key[:-1]+","+to_extend+"} "+value)
        else:
            output.append(key+"{"+to_extend+"} "+value)
    return "\n".join(output)

@app.route("/healthcheck")
def healthcheck():
    """ Healthcheck """
    d = docker.from_env(timeout=1)  #pylint: disable=invalid-name

    if d:
        return "OK"
    else:
        return 500, "Docker fail"

@app.route("/metrics_all")
def main():
    """ Collect all metrics """
    d = docker.from_env(timeout=2)  #pylint: disable=invalid-name

    result = []
    n = None    #pylint: disable=invalid-name
    attempts = 0
    while not n:
        try:
            n = d.networks.get("metrics-network")   #pylint: disable=invalid-name
        except:
            attempts += 1
        if attempts >= 3:
            return Response("no network found", mimetype='text/plain')
        if not n:
            sleep(0.1)

    # Prepate targets for async loop
    targets = {}
    if not n.attrs.get('Containers'):
        return Response("", mimetype='text/plain')

    for (k, v) in n.attrs['Containers'].items():    #pylint: disable=invalid-name
        if k == SELF_DOCKER_ID:
            continue
        try:
            c = d.containers.get(k) #pylint: disable=invalid-name
            (port, proto) = list(c.attrs['NetworkSettings']['Ports'].keys())[0].split("/")
            (ip, mask) = v['IPv4Address'].split("/")    #pylint: disable=invalid-name
        except:
            print("fail get ", k)
            continue
        url = "http://{}:{}/metrics".format(ip, port)

        to_extend = 'node_name="{}",container="{}"'.format(DOCKER_HOST_NAME, c.attrs['Name'])
        if "com.docker.swarm.service.name" in c.attrs["Config"]["Labels"]:
            to_extend += ',service="{}"'.format(
                c.attrs["Config"]["Labels"]["com.docker.swarm.service.name"])

        targets[url] = to_extend

    s = Session()   #pylint: disable=invalid-name
    s.mount("http://",
            HTTPAdapter(max_retries=Retry(total=3, status_forcelist=[500, 503]))
           )
    for (url, to_extend) in targets.items():
        try:
            r = s.get(url, timeout=2.0)    #pylint: disable=invalid-name
            if r.status_code != 200:
                continue
            if r.text:
                result.append(extend_metrics(r.text, to_extend)+"\n")
        except:
            pass

    return Response("".join(result), mimetype='text/plain')

if __name__ == "__main__":
    with open("/proc/1/cpuset", "r") as f:
        SELF_DOCKER_ID = f.read().split("/")[-1].rstrip()
    DOCKER_HOST_NAME = docker.from_env().info()['Name']
    app.run(debug=True, host='0.0.0.0')
