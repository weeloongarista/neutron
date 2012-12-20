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
from quantum.plugins.openvswitch.drivers.arista import AristaRPCWrapper
import mox
import unittest


class AristaRPCWrapperTestCase(unittest.TestCase):

    def setUp(self):
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()

    def test_raises_exception_on_wrong_configuration(self):
        conf = self.mocker.CreateMock(cfg.CONF)

        conf.arista_eapi_user = None
        conf.arista_eapi_pass = None
        conf.arista_eapi_host = None

        self.mocker.ReplayAll()

        self.assertRaises(QuantumException, AristaRPCWrapper, conf)
