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

import inspect

from quantum.common import exceptions
from quantum.common.hardware_driver.drivers import dummy
from quantum.extensions import portbindings
from quantum.openstack.common import cfg
from quantum.openstack.common import importutils
from quantum.openstack.common import log as logging


LOG = logging.getLogger(__name__)

HARDWARE_DRIVER_OPTS = [
    cfg.ListOpt('hardware_drivers',
                default=('quantum.common.hardware_driver.drivers.'
                         'dummy.DummyDriver'),
                help=_('Hardware driver used as a backend.'))
]


cfg.CONF.register_opts(HARDWARE_DRIVER_OPTS, "HARDWARE_DRIVER")


class InvalidDelegateError(exceptions.QuantumException):
    message = _('%(msg)s')


class DriverConfigError(exceptions.QuantumException):
    message = _('%(msg)s')


class DriverAdapter(object):
    """Adapts hardware driver API to a quantum plugin.

    Plugin adopting given class must support portbindings extension.
    Plugin MUST provide delegate which returns segmentation ID for a given
    network ID:
        lambda network_id: segmentation_id_for(network_id)
    """

    required_options = ['hardware_drivers']
    drivers_available = False

    def __init__(self, get_segmentation_id_delegate):
        """Contsructs adapter object.

        :param get_segmentation_id_delegate: function returning segmentation ID
        for a given network ID. Must have one argument.
        """
        config = cfg.CONF.HARDWARE_DRIVER

        self._verify_get_segmentation_id(get_segmentation_id_delegate)
        self._verify_configuration()

        self._get_segmentation_id = get_segmentation_id_delegate

        self._drivers = []

        # leave unique driver names
        hw_drivers = self._unique(config['hardware_drivers'])
        for driver in hw_drivers:
            hw_driver_class = importutils.import_class(driver)
            if hw_driver_class is not dummy.DummyDriver:
                hw_driver = hw_driver_class()
                self._drivers.append(hw_driver)

        if self._drivers:
            self.drivers_available = True

    def on_port_create(self, port):
        if not self.drivers_available:
            return

        p = port['port']
        host = p.get(portbindings.HOST_ID)

        if host:
            network_id = p['network_id']
            segmentation_id = self._get_segmentation_id(network_id)

            for driver in self._drivers:
                driver.plug_host(network_id, segmentation_id, host)

    def on_port_update(self, port, network_id):
        port['port']['network_id'] = network_id
        self.on_port_create(port)

    def on_network_create(self, network):
        if not self.drivers_available:
            return

        for driver in self._drivers:
            driver.create_network(network['id'])

    def on_network_update(self, network_id, network):
        if not self.drivers_available:
            return
        # TODO: analize what has changed and then act appropriately

    def on_network_delete(self, network_id):
        if not self.drivers_available:
            return

        for driver in self._drivers:
            driver.delete_network(network_id)

    def _verify_get_segmentation_id(self, get_segmentation_id_delegate):
        delegate_valid = (get_segmentation_id_delegate and
                          inspect.isroutine(get_segmentation_id_delegate))

        if not delegate_valid:
            msg = _('Invalid get_segmentation_id routine passed.')
            LOG.error(msg)
            raise InvalidDelegateError(msg=msg)

    def _verify_configuration(self):
        config = cfg.CONF.HARDWARE_DRIVER
        for opt in self.required_options:
            if opt not in config or config[opt] is None:
                msg = _('Required option %s is not set') % opt
                LOG.error(msg)
                raise DriverConfigError(msg=msg)

    def _unique(self, sequence):
        if type(sequence) is str:
            return [sequence]
        keys = {}
        for el in sequence:
            keys[el] = 1
        return keys.keys()
