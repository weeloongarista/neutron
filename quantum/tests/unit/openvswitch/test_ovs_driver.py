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

import mock
import unittest2 as unittest

from quantum.openstack.common import cfg
from quantum.common.hardware_driver import driver_adapter
from quantum.common.hardware_driver import driver_api


class FakeOVSDriver(driver_api.HardwareDriverAPI):
    def create_network(self, network_id):
        pass

    def plug_host(self, network_id, segmentation_id, host_id):
        pass

    def unplug_host(self, network_id, segmentation_id, host_id):
        pass

    def delete_network(self, network_id):
        pass


class OVSDriverAdapterTestCase(unittest.TestCase):
    """
    Tests for the OVSDriverAdapter class.
    """

    def _config_multiple_drivers(self):
        dummy_drv_str = ('quantum.common.hardware_driver.'
                         'drivers.dummy.DummyDriver')
        fake_drv_str = ('quantum.tests.unit.openvswitch.'
                        'test_ovs_driver.FakeOVSDriver')
        drivers_cfg = [dummy_drv_str, fake_drv_str]

        cfg.CONF.set_override('hw_drivers', drivers_cfg, 'HW_DRIVER')

    @classmethod
    def _valid_get_vlan_id(net_id):
        return '1234'

    def test_calls_all_drivers(self):
        self._config_multiple_drivers()

        drv = driver_adapter.DriverAdapter(self._valid_get_vlan_id)
        net_id = '123'
        network = {'id': net_id}

        fake_dummy_drv = mock.MagicMock()
        fake_ovs_drv = mock.MagicMock()

        drv._drivers = [fake_dummy_drv, fake_ovs_drv]

        drv.on_network_create(network)

        fake_dummy_drv.create_network.assert_called_once_with(net_id)
        fake_ovs_drv.create_network.assert_called_once_with(net_id)

    def test_error_is_raised_on_invalid_configuration(self):
        # Config values should not be None
        cfg.CONF.set_override('hw_drivers', None, 'HW_DRIVER')
        cfg.CONF.set_override('hw_driver_segmentation_type', None,
                              'HW_DRIVER')

        self.assertRaises(driver_adapter.DriverConfigError,
                          driver_adapter.DriverAdapter,
                          self._valid_get_vlan_id)
