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
import sqlalchemy

import quantum.db.api as db
from quantum.db import model_base
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
               help=_('Arista vEOS host IP')),
    cfg.StrOpt('arista_segmentation_type',
               default=driver_api.VLAN_SEGMENTATION,
               help=_('L2 segmentation type to be used on hardware routers. '
                      'One of vlan or tunnel is supported.'))
]

cfg.CONF.register_opts(ARISTA_DRIVER_OPTS, "ARISTA_DRIVER")


class AristaRpcError(exceptions.QuantumException):
    message = _('%(msg)s')


class AristaConfigError(exceptions.QuantumException):
    message = _('%(msg)s')


# TODO: Move to a separate file
class ProvisionedNetsStorage(object):
    class AristaProvisionedNets(model_base.BASEV2):
        """
        Stores VLANs provisioned on Arista vEOS. Allows to limit nubmer of RPC
        calls to the vEOS command API in case VLAN was provisioned before.
        """
        __tablename__ = 'arista_provisioned_nets'

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        network_id = sqlalchemy.Column(sqlalchemy.String(36))
        segmentation_id = sqlalchemy.Column(sqlalchemy.Integer)
        host_id = sqlalchemy.Column(sqlalchemy.String(255))

        def __init__(self, network_id, segmentation_id=None, host_id=None):
            self.network_id = network_id
            self.segmentation_id = segmentation_id
            self.host_id = host_id

        def __repr__(self):
            return "<AristaProvisionedNets(%s,%d,%s)>" % (self.network_id,
                                                          self.segmentation_id,
                                                          self.host_id)

        def veos_representation(self):
            segm_type = cfg.CONF.ARISTA_DRIVER['arista_segmentation_type']

            return {'hostId': self.host_id,
                    'networkId': self.network_id,
                    'segmentationId': self.segmentation_id,
                    'segmentationType': segm_type}

    def initialize(self):
        db.configure_db()

    def tear_down(self):
        db.clear_db()

    def remember_host(self, network_id, segmentation_id, host_id):
        session = db.get_session()
        with session.begin():
            net = (session.query(self.AristaProvisionedNets).
                   filter_by(network_id=network_id).first())

            if net and not net.segmentation_id and not net.host_id:
                net.segmentation_id = segmentation_id
                net.host_id = host_id
            else:
                provisioned_vlans = self.AristaProvisionedNets(network_id,
                                                               segmentation_id,
                                                               host_id)
                session.add(provisioned_vlans)

    def forget_host(self, network_id, host_id):
        session = db.get_session()
        with session.begin():
            (session.query(self.AristaProvisionedNets).
             filter_by(network_id=network_id, host_id=host_id).
             delete())

    def remember_network(self, network_id):
        session = db.get_session()
        with session.begin():
            net = (session.query(self.AristaProvisionedNets).
                   filter_by(network_id=network_id).first())

            if not net:
                net = self.AristaProvisionedNets(network_id)
                session.add(net)

    def forget_network(self, network_id):
        session = db.get_session()
        with session.begin():
            (session.query(self.AristaProvisionedNets).
             filter_by(network_id=network_id).
             delete())

    def is_network_provisioned(self, network_id,
                               segmentation_id=None,
                               host_id=None):
        session = db.get_session()
        with session.begin():
            num_nets = 0
            if not segmentation_id and not host_id:
                num_nets = (session.query(self.AristaProvisionedNets).
                            filter_by(network_id=network_id).count())
            else:
                num_nets = (session.query(self.AristaProvisionedNets).
                            filter_by(network_id=network_id,
                                      segmentation_id=segmentation_id,
                                      host_id=host_id).count())
            return num_nets > 0

    def get_all(self):
        session = db.get_session()
        with session.begin():
            return session.query(self.AristaProvisionedNets).all()

    def num_nets_provisioned(self):
        session = db.get_session()
        with session.begin():
            return session.query(self.AristaProvisionedNets).count()

    def num_hosts_for_net(self, network_id):
        session = db.get_session()
        with session.begin():
            return (session.query(self.AristaProvisionedNets).
                    filter_by(network_id=network_id).count())

    def get_all_hosts_for_net(self, network_id):
        session = db.get_session()
        with session.begin():
            return (session.query(self.AristaProvisionedNets).
                    filter_by(network_id=network_id).all())

    def store_provisioned_vlans(self, networks):
        for net in networks:
            self.remember_host(net['networkId'],
                               net['segmentationId'],
                               net['hostId'])

    def get_network_list(self):
        """Returns all networks in vEOS-compatible format.

        See AristaRPCWrapper.get_network_list() for return value format."""
        session = db.get_session()
        with session.begin():
            all_nets = session.query(self.AristaProvisionedNets).all()
            res = {}
            for net in all_nets:
                all_hosts = self.get_all_hosts_for_net(net.network_id)
                hosts = [host.host_id for host in all_hosts]
                res[net.network_id] = net.veos_representation()
                res[net.network_id]['hostId'] = hosts
            return res


class AristaRPCWrapper(object):
    """Wraps Arista JSON RPC.

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
        """Returns dict of all networks known by vEOS.

        :returns: dictionary with the following fields:
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
        """Returns list of VLANs for a given network.

        :param network_id:
        """
        net_list = self.get_network_list()

        for net in net_list:
            if net['network_id'] == network_id:
                return net

        return None

    def plug_host_into_vlan(self, network_id, vlan_id, host):
        """Creates VLAN between TOR and compute host.

        :param network_id: globally unique quantum network identifier
        :param vlan_id: VLAN ID
        :param host: compute node to be connected to a VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'type vlan id %s host %s' % (vlan_id, host)]
        self._run_openstack_cmd(cmds)

    def unplug_host_from_vlan(self, network_id, vlan_id, host_id):
        """Removes previously configured VLAN between TOR and a host.

        :param network_id: globally unique quantum network identifier
        :param vlan_id: VLAN ID
        :param host_id: target host to remove VLAN
        """
        cmds = ['tenant-network %s' % network_id,
                'no type vlan id %s host id %s' % (vlan_id, host_id)]
        self._run_openstack_cmd(cmds)

    def delete_network(self, network_id):
        """Deletes all tenant networks.

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


# TODO: add support for non-vlan mode (use checks before calling
#       plug_host_Into_vlan())
class SyncService(object):
    def __init__(self):
        self._db = ProvisionedNetsStorage()
        self._rpc = AristaRPCWrapper()

    def is_synchronized(self):
        """Checks whether quantum DB is in sync with vEOS DB"""
        veos_net_list = self._rpc.get_network_list()
        db_net_list = self._db.get_network_list()

        if veos_net_list != db_net_list:
            return False

        return True

    def synchronize(self):
        """Sends data to vEOS which differs from quantum DB."""
        veos_net_list = self._rpc.get_network_list()
        db_net_list = self._db.get_network_list()

        for net_id in db_net_list:
            db_net = db_net_list[net_id]

            # if network does not exist on vEOS
            if net_id not in veos_net_list:
                self._send_network_configuration(db_net_list, net_id)
            # if network exists, but hosts do not match
            elif db_net != veos_net_list[net_id]:
                veos_net = veos_net_list[net_id]
                if db_net['hostId'] != veos_net['hostId']:
                    self._plug_missing_hosts(net_id, db_net, veos_net)

    def _send_network_configuration(self, db_net_list, net_id):
        for host in db_net_list[net_id]['hostId']:
            segm_id = db_net_list[net_id]['segmentationId']
            self._rpc.plug_host_into_vlan(net_id, segm_id, host)

    def _plug_missing_hosts(self, net_id, db_net, veos_net):
        db_hosts = set(db_net['hostId'])
        veos_hosts = set(veos_net['hostId'])
        missing_hosts = db_hosts - veos_hosts
        vlan_id = db_net['segmentationId']
        for host in missing_hosts:
            self._rpc.plug_host_into_vlan(net_id, vlan_id, host)


class AristaDriver(driver_api.HardwareDriverAPI):
    """OVS driver for Arista networking hardware.

    Currently works in VLAN mode only. Remembers all VLANs provisioned. Does
    not send VLAN provisioning request if the VLAN has already been
    provisioned before for the given port.
    """

    def __init__(self, rpc=None, net_storage=ProvisionedNetsStorage()):
        if rpc is None:
            self.rpc = AristaRPCWrapper()
        else:
            self.rpc = rpc

        self.net_storage = net_storage
        self.net_storage.initialize()

        config = cfg.CONF.ARISTA_DRIVER
        self.segmentation_type = config['arista_segmentation_type']

    def create_network(self, network_id):
        self.net_storage.remember_network(network_id)

    def delete_network(self, network_id):
        if self.net_storage.is_network_provisioned(network_id):
            self.rpc.delete_network(network_id)
            self.net_storage.forget_network(network_id)

    def unplug_host(self, network_id, segmentation_id, host_id):
        storage = self.net_storage
        was_provisioned = storage.is_network_provisioned(network_id,
                                                         segmentation_id,
                                                         host_id)

        if was_provisioned:
            if self._vlans_used():
                self.rpc.unplug_host_from_vlan(network_id, segmentation_id,
                                               host_id)
            storage.forget_host(network_id, host_id)

    def plug_host(self, network_id, segmentation_id, host_id):
        storage = self.net_storage
        already_provisioned = storage.is_network_provisioned(network_id,
                                                             segmentation_id,
                                                             host_id)

        if not already_provisioned:
            if self._vlans_used():
                self.rpc.plug_host_into_vlan(network_id,
                                             segmentation_id,
                                             host_id)

        storage.remember_host(network_id, segmentation_id, host_id)

    def _vlans_used(self):
        return self._segm_type_used(driver_api.VLAN_SEGMENTATION)

    def _segm_type_used(self, segm_type):
        return self.segmentation_type == segm_type
