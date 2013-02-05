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

from quantum.common import exceptions
from quantum.openstack.common import cfg
from quantum.openstack.common import importutils
from quantum.openstack.common import log as logging
from quantum.plugins.openvswitch import ovs_db_v2
from quantum.plugins.openvswitch.drivers import dummy


LOG = logging.getLogger(__name__)

OVS_DRIVER_OPTS = [
    cfg.ListOpt('ovs_drivers',
                default=('quantum.plugins.openvswitch.drivers.'
                         'dummy.DummyOVSDriver'),
                help=_('OVS driver used as a backend.')),
    cfg.StrOpt('ovs_driver_segmentation_type',
               default='vlan',
               help=_('L2 segmentation type to be used on hardware routers. '
                      'One of vlan or tunnel is supported.'))
]


cfg.CONF.register_opts(OVS_DRIVER_OPTS, "OVS_DRIVER")


class OVSDriverConfigError(exceptions.QuantumException):
    message = _('%(msg)s')


class OVSDriverAdapter(object):
    """
    Adapts OVS driver API to OVS plugin incoming arguments.
    """

    # TODO: Refactor to remove 'if not self.drivers_available:' check in the
    #       beginning of each method (wrapper?).
    required_options = ['ovs_driver_segmentation_type', 'ovs_drivers']
    drivers_available = False

    def __init__(self):
        config = cfg.CONF.OVS_DRIVER

        for opt in self.required_options:
            if opt not in config or config[opt] is None:
                msg = _('Required option %s is not set') % opt
                LOG.error(msg)
                raise OVSDriverConfigError(msg=msg)

        self._drivers = []
        segm_type = config['ovs_driver_segmentation_type']

        # leave unique driver names
        ovs_drivers = self._unique(config['ovs_drivers'])
        for driver in ovs_drivers:
            ovs_driver_class = importutils.import_class(driver)
            if ovs_driver_class is not dummy.DummyOVSDriver:
                ovs_driver = ovs_driver_class()
                ovs_driver.segmentation_type = segm_type
                self._drivers.append(ovs_driver)

        if self._drivers:
            OVSDriverAdapter.drivers_available = True

    def on_port_create(self, context, port):
        if not self.drivers_available:
            return

        p = port['port']
        host = p.get('hostname')

        # If 'hostname' is not provided, the user has not booted nova instance
        # yet, do nothing.
        if host:
            network_id = p['network_id']
            binding = ovs_db_v2.get_network_binding(None, network_id)
            segmentation_id = binding.segmentation_id

            for driver in self._drivers:
                driver.plug_host(network_id, segmentation_id, host)

        self._do_plug_host(port['port'])

    def on_port_update(self, context, port):
        self.on_port_create(context, port)

    def on_network_create(self, context, network):
        if not self.drivers_available:
            return

        for driver in self._drivers:
            driver.create_tenant_network(network['id'])

    def on_network_update(self, context, network_id, network):
        if not self.drivers_available:
            return
        # TODO: analize what has changed and then act appropriately

    def on_network_delete(self, context, network_id):
        if not self.drivers_available:
            return

        for driver in self._drivers:
            driver.delete_tenant_network(network_id)

    def _unique(self, sequence):
        keys = {}
        for el in sequence:
            keys[el] = 1
        return keys.keys()
