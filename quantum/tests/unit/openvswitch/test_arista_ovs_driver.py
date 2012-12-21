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

from mox import IsA
from quantum.plugins.openvswitch.drivers.arista import AristaException
from quantum.plugins.openvswitch.drivers.arista import AristaRPCWrapper
import mox
import unittest


class FakeConfig(object):
    def __init__(self, initial_value=None):
        required_options = AristaRPCWrapper.required_options
        self._dict = {opt: initial_value for opt in required_options}

    def get(self, item):
        return self[item]

    def __getattr__(self, attr):
        return self[attr]

    def __getitem__(self, item):
        return self._dict[item]


class AristaRPCWrapperTestCase(unittest.TestCase):
    def test_raises_exception_on_wrong_configuration(self):
        fake_config = FakeConfig()
        self.assertRaises(AristaException, AristaRPCWrapper, fake_config)

    def test_no_exception_on_correct_configuration(self):
        fake_config = FakeConfig('some_value')

        obj = AristaRPCWrapper(fake_config)

        self.assertNotEqual(obj, None)

    def test_rpc_response_sent(self):
        mocker = mox.Mox()

        fake_config = FakeConfig('some_value')

        drv = AristaRPCWrapper(fake_config)
        mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(IsA(list))

        mocker.ReplayAll()

        network_id = 123
        vlan_id = 123
        host_id = 123
        drv.provision_vlan(network_id, vlan_id, host_id)

        mocker.VerifyAll()
