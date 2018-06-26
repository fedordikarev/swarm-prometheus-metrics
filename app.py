#!/usr/bin/env python

from flask import Flask
from flask import jsonify
from flask import Response

import docker
import requests

app = Flask(__name__)

SELF_DOCKER_ID = None
DOCKER_HOST_NAME = None

def extend_metrics(text, to_extend):
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
            key_name = key[:-1]
            output.append(key[:-1]+","+to_extend+"} "+value)
        else:
            output.append(key+"{"+to_extend+"} "+value)
    return "\n".join(output)

@app.route("/metrics_all")
def main():
    d = docker.from_env()

    result = []
    try:
        n = d.networks.get("metrics-network")
    except:
        return ""

    for (k, v) in n.attrs['Containers'].items():
        print("DEBUG", k, v)
        if k == SELF_DOCKER_ID:
            continue
        try:
            c = d.containers.get(k)
            (port, proto) = list(c.attrs['NetworkSettings']['Ports'].keys())[0].split("/")
            (ip, mask) = v['IPv4Address'].split("/")
        except:
            print("fail get ", k)
            continue
        try:
            r = requests.get("http://{}:{}/metrics".format(ip, port), timeout=10)
            if r.status_code != 200:
                continue
            # print(r.text)
            to_extend = 'node_name="{}",container="{}"'.format(DOCKER_HOST_NAME, c.attrs['Name'])
            if "com.docker.swarm.service.name" in c.attrs["Config"]["Labels"]:
                to_extend += ',service="{}"'.format(c.attrs["Config"]["Labels"]["com.docker.swarm.service.name"])
            if r.text:
                result.append(extend_metrics(r.text, to_extend)+"\n")
            # result.append({c.attrs['Name']: extend_metrics(r.text, to_extend)})
            # result.append({c.attrs['Name']: "http://{}:{}/metrics".format(ip, port)})
            # return json.dumps(result)
        except:
            print(c.attrs['Name'], "no metrics")

    return Response("".join(result), mimetype='text/plain')

if __name__ == "__main__":
    with open("/proc/1/cpuset", "r") as f:
        SELF_DOCKER_ID = f.read().split("/")[-1].rstrip()
    DOCKER_HOST_NAME = docker.from_env().info()['Name']
    app.run(debug=True, host='0.0.0.0')
