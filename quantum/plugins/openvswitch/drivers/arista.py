# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (c) 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from quantum.plugins.openvswitch.common.config import cfg
from quantum.plugins.openvswitch.ovs_driver_api import OVSDriverAPI
import jsonrpclib


class AristaRPCWrapper(object):
    """
    Wraps Arista JSON RPC.
    """

    def __init__(self):
        eapi_info = {'user': cfg.CONF.arista_eapi_user,
                     'pass': cfg.CONF.arista_eapi_pass,
                     'host': cfg.CONF.arista_eapi_host}

        eapi_server_url = 'https://%(user)s:%(pass)s@%(host)s/eapi' % eapi_info
        self._server = jsonrpclib.Server(eapi_server_url)

    def get_network_list(self):
        return self._server.runCli(cmds=['show openstack'])

    def get_network_info(self, network_id):
        net_list = self.get_network_list()

        for net in net_list:
            if net['network_id'] == network_id:
                return net

        return None


class AristaOVSDriver(OVSDriverAPI):
    """
    OVS driver for Arista networking hardware.
    """

    def __init__(self):
        pass

    def create_tenant_network(self, context, network_id, segmentation_id,
                              segmentation_type):
        pass

    def delete_tenant_network(self, context, network_id):
        pass

    def unplug_host(self, context, network_id, host_id):
        pass

    def plug_host(self, context, network_id, host_id):
        pass

    def get_tenant_network(self, context, networkd_id=None):
        pass
