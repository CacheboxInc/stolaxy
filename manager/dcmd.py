#!/usr/bin/env python3

import subprocess

def dcmd(cmd, hosts, undo = None):
    """
    execute cmd on hosts. returns True if cmd was successful on all nodes. 
    If there was a failure on any node then the command is undone on the
    relevant hosts.
    """

    success = []
    try:
        for host in hosts:
            _cmds = [
                "ssh",
                host,
                cmd,
                ]

            _cmd = subprocess.Popen(cmds, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out, err = _cmd.communicate()
            if _cmd.returncode != 0:
                raise Exception('error')
            
            success.append(host)
    except:
        if undo is not None:
            for host in success:
                _cmds = [
                    "ssh",
                    host,
                    undo
                    ]
                _cmd = subprocess.Popen(cmds, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                _cmd.communicate()

        return False

    else:
        return True
