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

from quantum.common.exceptions import QuantumException
from quantum.plugins.openvswitch.common.config import cfg
from quantum.plugins.openvswitch.ovs_driver_api import OVSDriverAPI
import jsonrpclib


ARISTA_CONF = cfg.CONF.ARISTA_DRIVER


class AristaException(QuantumException):
    message = _('%(msg)s')


class AristaRPCWrapper(object):
    """
    Wraps Arista JSON RPC.
    vEOS - operating system used in Arista hardware
    EAPI - JSON RPC API provided by Arista vEOS
    """
    required_options = [el for el in ARISTA_CONF]

    def __init__(self, config=ARISTA_CONF):
        self._server = jsonrpclib.Server(self._eapi_host_url(config))

    def get_network_list(self):
        """
        Returns list of all networs know by vEOS
        """
        return self._run_openstack_cmd(['show openstack'])

    def get_network_info(self, network_id):
        """
        Returns list of VLANs for a given TODO: tenant (network?)
        :param network_id:
        """
        net_list = self.get_network_list()

        for net in net_list:
            if net['network_id'] == network_id:
                return net

        return None

    def provision_vlan(self, network_id, vlan_id, host):
        """
        Creates VLAN between TOR and compute host
        :param network_id: tenant network ID TODO: tenant or network?
        :param vlan_id: VLAN ID
        :param host: compute node to be connected to a VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'type vlan id %s host %s' % (vlan_id, host)]
        self._run_openstack_cmd(cmds)

    def delete_tenant_network(self, network_id):
        """
        Deletes all tenant networks
        :param network_id: TODO: tenant ID?
        """
        cmds = ['no tenant-network %s' % network_id]
        self._run_openstack_cmd(cmds)

    def delete_vlan(self, network_id, vlan_id, host_id):
        """
        Removes previously configured VLAN between TOR and a host
        :param network_id: TODO: tenant or network ID?
        :param vlan_id: VLAN ID
        :param host_id: target host to remove VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'no type vlan id %s host id %s' % vlan_id, host_id]
        self._run_openstack_cmd(cmds)

    def _run_openstack_cmd(self, cmds):
        if cmds is not list:
            cmds = [cmds]

        start = ['configure terminal', 'management openstack']
        end = ['exit']

        full_command = start + cmds + end

        return self._server.runCli(cmds=full_command)

    def _eapi_host_url(self, config):
        self._validate_config(config)

        eapi_server_url = 'https://%s:%s@%s/eapi' % (config.arista_eapi_user,
                                                     config.arista_eapi_pass,
                                                     config.arista_eapi_host)

        return eapi_server_url

    def _validate_config(self, config):
        for option in self.required_options:
            if config.get(option) is None:
                raise AristaException(msg='Required option %s is not set' %
                                      option)


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
