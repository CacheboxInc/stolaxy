#!/usr/bin/env python3

import subprocess

def docker_cmd(host, instance, cmd):
    print (cmd, 'on docker instance', host, instance)

    cmd = (
        "ssh",
        host,
        "docker",
        cmd,
        instance
        )

    cmdp = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = cmdp.communicate()
    
    return (cmdp.returncode, out, err)

def cleanup_instance(host, instance):
    print ('cleaning up docker instance', host, instance)

    ret, out, err = docker_cmd(host, instance, 'stop')
    ret, out, err = docker_cmd(host, instance, 'rm')

    return ret
