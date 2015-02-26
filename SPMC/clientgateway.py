#!/usr/bin/env python3

import os

class ClientGateway(object):
    """
    implements the client gateway node creation and launch logic. end
    users connect to this node via ssh or REST or web gui to manage
    their big data platform services.
    """

    def create(self, *args, **kwargs):
        os.system(
RUN cd ~ \
    && echo -e 'y\n'|ssh-keygen -b 1024 -q -t dsa -N "" -f /cachebox/bduser \
    && mkdir .ssh \
    && chmod 700 .ssh \
    && cat /cachebox/bduser.pub >> .ssh/authorized_keys \
    && chmod 600 .ssh/authorized_keys \
    && chown root .ssh \
    && chown root .ssh/authorized_keys \
    && mv /cachebox/bduser .ssh/bduser.pem

