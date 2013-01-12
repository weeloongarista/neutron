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
from quantum.plugins.openvswitch.ovs_driver_api import TUNNEL_SEGMENTATION
from quantum.plugins.openvswitch.ovs_driver_api import VLAN_SEGMENTATION
import jsonrpclib
import logging


LOG = logging.getLogger(__name__)


ARISTA_CONF = cfg.CONF.OVS_DRIVER


class AristaException(QuantumException):
    message = _('%(msg)s')

    def __init__(self, message):
        self.message = message
        super(AristaException, self).__init__()


class AristaRPCWrapper(object):
    """
    Wraps Arista JSON RPC.
    vEOS - operating system used in Arista hardware
    EAPI - JSON RPC API provided by Arista vEOS
    TOR - Top Of Rack switch, Arista HW switch
    """
    required_options = ['arista_eapi_pass',
                        'arista_eapi_host',
                        'arista_eapi_user']

    def __init__(self, config=ARISTA_CONF):
        self._server = jsonrpclib.Server(self._eapi_host_url(config))

    def get_network_list(self):
        """
        Returns list of all networks known by vEOS
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
        LOG.info('plug_host_into_vlan')
        LOG.info('hostname: %s' % host)
        LOG.info('network_id: %s' % network_id)
        LOG.info('vlan_id: %s' % vlan_id)

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
                'no type vlan id %s host id %s' % vlan_id, host_id]
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

        full_command = ['configure terminal', 'management openstack']
        for cmd in commands:
            full_command.append(cmd)
        full_command.append('exit')

        LOG.info('Executing command on Arista vEOS: %s', full_command)

        ret = None

        try:
            # this returns array of return values for every command in
            # full_command list
            ret = self._server.runCli(cmds=full_command)

            # Remove return values for 'configure terminal',
            # 'management openstack' and 'exit' commands
            ret = ret[2:-1]
        except Exception as ex:
            msg = ('Error %s while trying to execute commands %s on vEOS '
                   '%s') % (ex.message, full_command,
                            ARISTA_CONF.arista_eapi_host)
            LOG.error(msg)
            raise AristaException(msg)

        return ret

    def _eapi_host_url(self, config):
        self._validate_config(config)

        eapi_server_url = 'https://%s:%s@%s/eapi' % (config.arista_eapi_user,
                                                     config.arista_eapi_pass,
                                                     config.arista_eapi_host)

        return eapi_server_url

    def _validate_config(self, config):
        for option in self.required_options:
            if config.get(option) is None:
                msg = 'Required option %s is not set' % option
                LOG.error(msg)
                raise AristaException(msg)


class AristaOVSDriver(OVSDriverAPI):
    """
    OVS driver for Arista networking hardware. Currently works in VLAN mode
    only, tunnelling L2 segregation is not supported.
    """

    segmentation_type = ARISTA_CONF['ovs_driver_segmentation_type']

    def __init__(self, rpc=None):
        if rpc is None:
            self.rpc = AristaRPCWrapper()
        else:
            self.rpc = rpc

        self._provisioned_nets = self.rpc.get_network_list()

    def create_tenant_network(self, context, network_id):
        pass

    def delete_tenant_network(self, context, network_id):
        return self.rpc.delete_network(network_id)

    def unplug_host(self, context, network_id, segmentation_id, host_id):
        if self._vlans_used():
            self.rpc.unplug_host_from_vlan(network_id, segmentation_id,
                                           host_id)
        self._forget_network(network_id, segmentation_id, host_id)

    def plug_host(self, context, network_id, segmentation_id, host_id):
        already_provisioned = self._network_provisioned(network_id,
                                                        segmentation_id,
                                                        host_id)

        if not already_provisioned:
            if self._vlans_used():
                self.rpc.plug_host_into_vlan(network_id,
                                             segmentation_id,
                                             host_id)
            elif self._tunnels_used():
                # Does nothing currently
                pass

        self._remember_network(network_id, segmentation_id, host_id)

    def get_tenant_network(self, context, networkd_id=None):
        pass

    def _network_provisioned(self, network_id, segmentation_id, host_id):
        known_nets = self._provisioned_nets

        if network_id not in known_nets:
            return False

        known_segm_id = known_nets[network_id]['segmentationId']
        known_host_id = known_nets[network_id]['hostId']
        known_segm_type = known_nets[network_id]['segmentationType']

        return (known_segm_id == segmentation_id) and \
               (known_host_id == host_id) and \
               (self.segmentation_type == known_segm_type)

    def _remember_network(self, network_id, segmentation_id, host_id):
        # TODO: There must be a list of hostIds. Currently - single item.
        segmentation_type = ARISTA_CONF['ovs_driver_segmentation_type']
        self._provisioned_nets[network_id] = {
            'segmentationId': segmentation_id,
            'hostId': host_id,
            'segmentationType': segmentation_type
        }

    def _forget_network(self, network_id, segmentation_id, host_id):
        # TODO: There must be a list of hostIds. Currently - single item.
        del self._provisioned_nets[network_id]

    def _vlans_used(self):
        return self._segm_type_used(VLAN_SEGMENTATION)

    def _tunnels_used(self):
        return self._segm_type_used(TUNNEL_SEGMENTATION)

    def _segm_type_used(self, segm_type):
        return self.segmentation_type == segm_type
