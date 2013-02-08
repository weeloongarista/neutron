# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (c) 2013 OpenStack, LLC.
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

import jsonrpclib

from quantum.common import exceptions
from quantum.openstack.common import cfg
from quantum.openstack.common import log as logging
from quantum.common.hardware_driver import driver_api


LOG = logging.getLogger(__name__)


ARISTA_DRIVER_OPTS = [
    cfg.StrOpt('arista_eapi_user',
               default=None,
               help=_('Username for Arista vEOS')),
    cfg.StrOpt('arista_eapi_pass',
               default=None,
               help=_('Password for Arista vEOS')),
    cfg.StrOpt('arista_eapi_host',
               default=None,
               help=_('Arista vEOS host IP'))
]

cfg.CONF.register_opts(ARISTA_DRIVER_OPTS, "ARISTA_DRIVER")


class AristaRpcError(exceptions.QuantumException):
    message = _('%(msg)s')


class AristaConfigError(exceptions.QuantumException):
    message = _('%(msg)s')


class AristaRPCWrapper(object):
    """
    Wraps Arista JSON RPC.
    vEOS - operating system used on Arista hardware
    Command API - JSON RPC API provided by Arista vEOS
    TOR - Top Of Rack switch, Arista HW switch
    """
    required_options = ['arista_eapi_pass',
                        'arista_eapi_host',
                        'arista_eapi_user']

    def __init__(self):
        self._server = jsonrpclib.Server(self._eapi_host_url())

    def get_network_list(self):
        """
        Returns dict of all networks known by vEOS. The dict format is as
        follows:
           {networkId:
             {
               'hostId': [list of hosts connected to the network],
               'name': network name, currently quantum net id,
               'segmentationId': VLAN id,
               'segmentationType': L2 segmentation type; currently 'vlan' only
             }
           }
        """
        command_output = self._run_openstack_cmd(['show openstack'])
        networks = command_output[0]['networks']

        return networks

    def get_network_info(self, network_id):
        """
        Returns list of VLANs for a given network
        :param network_id:
        """
        net_list = self.get_network_list()

        for net in net_list:
            if net['network_id'] == network_id:
                return net

        return None

    def plug_host_into_vlan(self, network_id, vlan_id, host):
        """
        Creates VLAN between TOR and compute host
        :param network_id: globally unique quantum network identifier
        :param vlan_id: VLAN ID
        :param host: compute node to be connected to a VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'type vlan id %s host %s' % (vlan_id, host)]
        self._run_openstack_cmd(cmds)

    def unplug_host_from_vlan(self, network_id, vlan_id, host_id):
        """
        Removes previously configured VLAN between TOR and a host
        :param network_id: globally unique quantum network identifier
        :param vlan_id: VLAN ID
        :param host_id: target host to remove VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'no type vlan id %s host id %s' % (vlan_id, host_id)]
        self._run_openstack_cmd(cmds)

    def delete_network(self, network_id):
        """
        Deletes all tenant networks
        :param network_id: globally unique quantum network identifier
        """
        cmds = ['no tenant-network %s' % network_id]
        self._run_openstack_cmd(cmds)

    def _run_openstack_cmd(self, commands):
        if type(commands) is not list:
            commands = [commands]

        command_start = ['configure', 'management openstack']
        command_end = ['exit']
        full_command = command_start + commands + command_end

        LOG.info(_('Executing command on Arista vEOS: %s'), full_command)

        ret = None

        try:
            # this returns array of return values for every command in
            # full_command list
            ret = self._server.runCmds(cmds=full_command)

            # Remove return values for 'configure terminal',
            # 'management openstack' and 'exit' commands
            ret = ret[len(command_start):-len(command_end)]
        except Exception as error:
            host = cfg.CONF.ARISTA_DRIVER.arista_eapi_host
            msg = _('Error %(error)s while trying to execute commands '
                    '%(full_command)s on vEOS %(host)s') % locals()
            LOG.error(msg)
            raise AristaRpcError(msg=msg)

        return ret

    def _eapi_host_url(self):
        self._validate_config()

        user = cfg.CONF.ARISTA_DRIVER.arista_eapi_user
        pwd = cfg.CONF.ARISTA_DRIVER.arista_eapi_pass
        host = cfg.CONF.ARISTA_DRIVER.arista_eapi_host

        eapi_server_url = ('https://%(user)s:%(pwd)s@%(host)s/command-api' %
                           locals())

        return eapi_server_url

    def _validate_config(self):
        for option in self.required_options:
            if cfg.CONF.ARISTA_DRIVER.get(option) is None:
                msg = _('Required option %s is not set') % option
                LOG.error(msg)
                raise AristaConfigError(msg=msg)


class AristaDriver(driver_api.HardwareDriverAPI):
    """
    OVS driver for Arista networking hardware. Currently works in VLAN mode
    only. Remembers all VLANs provisioned. Does not send VLAN provisioning
    request if the VLAN has already been provisioned before for the given
    port.
    """

    def __init__(self, rpc=None):
        if rpc is None:
            self.rpc = AristaRPCWrapper()
        else:
            self.rpc = rpc

        self._provisioned_nets = self.rpc.get_network_list()
        self.segmentation_type = driver_api.VLAN_SEGMENTATION

    def create_network(self, network_id):
        self._remember_network(network_id)

    def delete_network(self, network_id):
        if self._is_network_provisioned(network_id):
            self.rpc.delete_network(network_id)
            self._forget_network(network_id)

    def unplug_host(self, network_id, segmentation_id, host_id):
        was_provisioned = self._is_network_provisioned(network_id,
                                                       segmentation_id,
                                                       host_id)

        if was_provisioned:
            if self._vlans_used():
                self.rpc.unplug_host_from_vlan(network_id, segmentation_id,
                                               host_id)
            self._forget_host(network_id, host_id)

    def plug_host(self, network_id, segmentation_id, host_id):
        already_provisioned = self._is_network_provisioned(network_id,
                                                           segmentation_id,
                                                           host_id)

        if not already_provisioned:
            if self._vlans_used():
                self.rpc.plug_host_into_vlan(network_id,
                                             segmentation_id,
                                             host_id)

        self._remember_host(network_id, segmentation_id, host_id)

    def _is_network_provisioned(self, network_id, segmentation_id=None,
                                host_id=None):
        known_nets = self._provisioned_nets

        if network_id not in known_nets:
            return False
        elif segmentation_id is None and host_id is None:
            return True

        known_segm_id = known_nets[network_id]['segmentationId']
        known_host_ids = known_nets[network_id]['hostId']

        return ((known_segm_id == segmentation_id) and
                any([host_id == h for h in known_host_ids]))

    def _remember_host(self, network_id, segmentation_id, host_id):
        nets = self._provisioned_nets
        if network_id in nets:
            hosts = nets[network_id]['hostId']
            hosts.append(host_id)
            nets[network_id]['hostId'] = hosts
            nets[network_id]['segmentationId'] = segmentation_id

    def _forget_host(self, network_id, host_id):
        nets = self._provisioned_nets
        if network_id in nets:
            hosts = nets[network_id]['hostId']
            if host_id in hosts:
                hosts.remove(host_id)

            # remove entire network if host list is empty
            if not hosts:
                self._forget_network(network_id)
            else:
                nets[network_id]['hostId'] = hosts

    def _remember_network(self, network_id):
        if network_id not in self._provisioned_nets:
            self._provisioned_nets[network_id] = {
                'segmentationId': None,
                'hostId': [],
                'segmentationType': self.segmentation_type
            }

    def _forget_network(self, network_id):
        del self._provisioned_nets[network_id]

    def _vlans_used(self):
        return self._segm_type_used(driver_api.VLAN_SEGMENTATION)

    def _segm_type_used(self, segm_type):
        return self.segmentation_type == segm_type
