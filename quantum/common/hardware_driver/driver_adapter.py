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
from quantum.common.hardware_driver.drivers import dummy
from quantum.extensions import portbindings
from quantum.openstack.common import cfg
from quantum.openstack.common import importutils
from quantum.openstack.common import log as logging


LOG = logging.getLogger(__name__)

HW_DRIVER_OPTS = [
    cfg.StrOpt('hw_driver',
               default=('quantum.common.hardware_driver.drivers.'
                        'dummy.DummyDriver'),
               help=_('OVS driver used as a backend.')),
    cfg.StrOpt('hw_driver_segmentation_type',
               default='vlan',
               help=_('L2 segmentation type to be used on hardware routers. '
                      'One of vlan or tunnel is supported.'))
]


cfg.CONF.register_opts(HW_DRIVER_OPTS, "HW_DRIVER")


class DriverConfigError(exceptions.QuantumException):
    message = _('%(msg)s')


class DriverAdapter(object):
    """
    Adapts hardware driver API to a quantum plugin.
    Plugin adopting given class must support portbindings extension.
    """

    required_options = ['hw_driver_segmentation_type', 'hw_driver']
    driver_available = False

    def __init__(self):
        for opt in self.required_options:
            if opt not in cfg.CONF.HW_DRIVER:
                msg = _('Required option %s is not set') % opt
                LOG.error(msg)
                raise DriverConfigError(msg=msg)

        driver_name = cfg.CONF.HW_DRIVER['hw_driver']
        segm_type = cfg.CONF.HW_DRIVER['hw_driver_segmentation_type']

        hw_driver_class = importutils.import_class(driver_name)

        self._driver = hw_driver_class()
        self._driver.segmentation_type = segm_type

        self.driver_available = (hw_driver_class is not dummy.DummyDriver)

    def on_port_create(self, port, segmentation_id):
        if not self.driver_available:
            return

        p = port['port']
        host = p.get(portbindings.HOST_ID)

        if host:
            network_id = p['network_id']

            self._driver.plug_host(network_id, segmentation_id, host)

    def on_port_update(self, port, network_id):
        port['port']['network_id'] = network_id
        self.on_port_create(port)

    def on_network_create(self, network):
        if not self.driver_available:
            return

        self._driver.create_network(network['id'])

    def on_network_update(self, network_id, network):
        if not self.driver_available:
            return
        # TODO: analize what has changed and then act appropriately

    def on_network_delete(self, network_id):
        if not self.driver_available:
            return

        self._driver.delete_network(network_id)
