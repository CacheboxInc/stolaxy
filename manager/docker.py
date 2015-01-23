#!/usr/bin/env python3

import subprocess

def cleanup_instance(host, instance):
    print ('cleaning up docker instance', host, instance)

    cmd = (
        "ssh",
        host,
        "docker",
        "stop",
        instance
        )

    stop = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = stop.communicate()
    
    # ignore the return value of stop

    cmd = (
        "ssh",
        host,
        "docker",
        "rm",
        instance
        )

    cleanup = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = cleanup.communicate()

    return cleanup.returncode
