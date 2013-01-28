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

import mox
import unittest

from quantum.openstack.common import cfg
from quantum.plugins.openvswitch.drivers.dummy import DummyOVSDriver
from quantum.plugins.openvswitch.ovs_driver_adapter import OVSDriverAdapter
from quantum.plugins.openvswitch.ovs_driver_adapter import OVSDriverConfigError
from quantum.plugins.openvswitch.ovs_driver_api import OVSDriverAPI


class FakeOVSDriver(OVSDriverAPI):
    def create_tenant_network(self, network_id):
        pass

    def plug_host(self, network_id, segmentation_id, host_id):
        pass

    def unplug_host(self, network_id, segmentation_id, host_id):
        pass

    def delete_tenant_network(self, network_id):
        pass

    def get_tenant_network(self, networkd_id=None):
        pass


class OVSDriverAdapterTestCase(unittest.TestCase):
    """
    Tests for the OVSDriverAdapter class.
    """

    def setUp(self):
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()

    def test_calls_all_drivers(self):
        dummy_drv_str = ('quantum.plugins.openvswitch.'
                         'drivers.dummy.DummyOVSDriver')
        fake_drv_str = ('quantum.tests.unit.openvswitch.'
                        'test_ovs_driver.FakeOVSDriver')
        drivers_cfg = [dummy_drv_str, fake_drv_str]

        cfg.CONF.set_override('ovs_drivers', drivers_cfg, 'OVS_DRIVER')
        drv = OVSDriverAdapter()
        context = None
        net_id = '123'
        network = {'id': net_id}

        fake_dummy_drv = self.mocker.CreateMock(DummyOVSDriver)
        fake_ovs_drv = self.mocker.CreateMock(FakeOVSDriver)

        fake_dummy_drv.create_tenant_network(net_id)
        fake_ovs_drv.create_tenant_network(net_id)

        drv._drivers = [fake_dummy_drv, fake_ovs_drv]

        self.mocker.ReplayAll()

        drv.on_network_create(context, network)

    def test_error_is_raised_on_invalid_configuration(self):
        # Config values should not be None
        cfg.CONF.set_override('ovs_drivers', None, 'OVS_DRIVER')
        cfg.CONF.set_override('ovs_driver_segmentation_type', None,
                              'OVS_DRIVER')

        self.assertRaises(OVSDriverConfigError, OVSDriverAdapter)
