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

from quantum.common.hardware_driver import driver_adapter
from quantum.common.hardware_driver import driver_api
from quantum.extensions import portbindings
from quantum.openstack.common import cfg


class FakeHwDriver(driver_api.HardwareDriverAPI):
    def create_network(self, network_id):
        pass

    def plug_host(self, network_id, segmentation_id, host_id):
        pass

    def unplug_host(self, network_id, segmentation_id, host_id):
        pass

    def delete_network(self, network_id):
        pass


class HardwareDriverAdapterTestCase(unittest.TestCase):
    """Tests for the HardwareDriverAdapter class."""

    def _config_multiple_drivers(self):
        dummy_drv_str = ('quantum.common.hardware_driver.'
                         'drivers.dummy.DummyDriver')
        fake_drv_str = ('quantum.tests.unit.hardware_driver.'
                        'test_hardware_driver_adapter.FakeHwDriver')
        drivers_cfg = [dummy_drv_str, fake_drv_str]

        cfg.CONF.set_override('hardware_drivers', drivers_cfg,
                              'HARDWARE_DRIVER')

    def _valid_get_segm_id(self):
        def get_vlan_id(_):
            return '123'
        return get_vlan_id

    def _invalid_get_segm_id(self):
        return object()

    def test_calls_all_drivers_on_create_network(self):
        self._config_multiple_drivers()

        drv = driver_adapter.DriverAdapter(self._valid_get_segm_id())
        net_id = '123'
        network = {'id': net_id}

        fake_dummy_drv = mock.MagicMock()
        fake_ovs_drv = mock.MagicMock()

        drv._drivers = [fake_dummy_drv, fake_ovs_drv]

        drv.on_network_create(network)

        fake_dummy_drv.create_network.assert_called_once_with(net_id)
        fake_ovs_drv.create_network.assert_called_once_with(net_id)

    def test_call_all_drivers_on_port_create_if_vm_boot(self):
        self._config_multiple_drivers()
        get_segm_id_delegate = self._valid_get_segm_id()
        drv = driver_adapter.DriverAdapter(get_segm_id_delegate)

        # when VM is booted, 'device_id' and 'device_owner' parameters are set
        # for a port
        net_id = 'net_id'
        vlan_id = get_segm_id_delegate(net_id)
        host_id = 'host1'
        port = {'port': {portbindings.HOST_ID: host_id,
                         'device_id': 'device_id',
                         'device_owner': 'device_owner',
                         'network_id': net_id}}

        fake_dummy_drv = mock.MagicMock()
        fake_hw_drv = mock.MagicMock()

        drv._drivers = [fake_dummy_drv, fake_hw_drv]

        drv.on_port_create(port)

        fake_dummy_drv.plug_host.assert_called_once_with(net_id, vlan_id,
                                                         host_id)
        fake_hw_drv.plug_host.assert_called_once_with(net_id, vlan_id, host_id)

    def test_doesnt_call_drivers_on_port_create_if_not_vm_boot(self):
        self._config_multiple_drivers()

        drv = driver_adapter.DriverAdapter(self._valid_get_segm_id())

        # when VM is booted, 'device_id' and 'device_owner' parameters are set
        # for a port
        port = {'port': {portbindings.HOST_ID: 'host1',
                         'network_id': 'net_id'}}

        fake_dummy_drv = mock.MagicMock()
        fake_hw_drv = mock.MagicMock()

        drv._drivers = [fake_dummy_drv, fake_hw_drv]

        drv.on_port_create(port)

        self.assertTrue(fake_dummy_drv.plug_host.call_args_list == [])
        self.assertTrue(fake_hw_drv.plug_host.call_args_list == [])

    def test_error_is_raised_on_invalid_get_segm_id_delegate(self):
        invalid_get_segm_id_delegate = self._invalid_get_segm_id()

        self.assertRaises(driver_adapter.InvalidDelegateError,
                          driver_adapter.DriverAdapter,
                          invalid_get_segm_id_delegate)

    def test_error_is_raised_on_invalid_configuration(self):
        # Config values should not be None
        cfg.CONF.set_override('hardware_drivers', None, 'HARDWARE_DRIVER')
        get_vlan_id_delegate = self._valid_get_segm_id()

        self.assertRaises(driver_adapter.DriverConfigError,
                          driver_adapter.DriverAdapter,
                          get_vlan_id_delegate)
