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
from quantum.common.hardware_driver import driver_api
from quantum.common.hardware_driver.drivers import arista


def clear_config():
    cfg.CONF.clear()


def setup_arista_wrapper_config(value=None):
    for opt in arista.AristaRPCWrapper.required_options:
        cfg.CONF.set_override(opt, value, "ARISTA_DRIVER")


def setup_valid_config():
    # Config is not valid if value is not set
    setup_arista_wrapper_config('value')


class AristaRPCWrapperInvalidConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.setup_invalid_config()  # Invalid config, required options not set

    def tearDown(self):
        clear_config()

    def setup_invalid_config(self):
        setup_arista_wrapper_config(None)

    def test_raises_exception_on_wrong_configuration(self):
        self.assertRaises(arista.AristaConfigError, arista.AristaRPCWrapper)


class PositiveRPCWrapperValidConfigTestCase(unittest.TestCase):
    def setUp(self):
        setup_valid_config()
        self.drv = arista.AristaRPCWrapper()
        self.drv._server = mock.MagicMock()

    def tearDown(self):
        clear_config()

    def test_no_exception_on_correct_configuration(self):
        self.assertNotEqual(self.drv, None)

    def test_plug_host_into_vlan_calls_rpc(self):
        network_id = 'net-id'
        vlan_id = 123
        host = 'host'

        self.drv.plug_host_into_vlan(network_id, vlan_id, host)

        self.drv._server.runCmds.assert_called_once_with(cmds=mock.ANY)

    def test_unplug_host_from_vlan_calls_rpc(self):
        network_id = 'net-id'
        vlan_id = 123
        host = 'host'
        self.drv.unplug_host_from_vlan(network_id, vlan_id, host)
        self.drv._server.runCmds.assert_called_once_with(cmds=mock.ANY)

    def test_delete_network_calls_rpc(self):
        network_id = 'net-id'
        self.drv.delete_network(network_id)
        self.drv._server.runCmds.assert_called_once_with(cmds=mock.ANY)

    def test_get_network_info_returns_none_when_no_such_net(self):
        unavailable_network_id = '12345'

        self.drv.get_network_list = mock.MagicMock()
        self.drv.get_network_list.return_value = []

        net_info = self.drv.get_network_info(unavailable_network_id)

        self.drv.get_network_list.assert_called_once_with()
        self.assertEqual(net_info, None, ('Network info must be "None"'
                                          'for unknown network'))

    def test_get_network_info_returns_info_for_available_net(self):
        valid_network_id = '12345'
        valid_net_info = {'network_id': valid_network_id,
                          'some_info': 'net info'}
        known_nets = [valid_net_info]

        self.drv.get_network_list = mock.MagicMock()
        self.drv.get_network_list.return_value = known_nets

        net_info = self.drv.get_network_info(valid_network_id)
        self.assertEqual(net_info, valid_net_info,
                         ('Must return network info for a valid net'))

    def test_rpc_is_sent_on_get_network_list(self):
        net = {'netId': 123, 'hostId': 'host1'}
        net_list_veos = {'networks': net}
        cli_ret = [{}, {}, net_list_veos, {}]

        self.drv._server.runCmds(cmds=mock.ANY)
        self.drv._server.runCmds.return_value = cli_ret

        net_list = self.drv.get_network_list()
        self.assertEqual(net_list, net, 'Networks should be the same')


class NegativeRPCWrapperTestCase(unittest.TestCase):
    def setUp(self):
        setup_valid_config()

    def tearDown(self):
        clear_config()

    def test_exception_is_raised_on_json_server_error(self):
        drv = arista.AristaRPCWrapper()

        drv._server = mock.MagicMock()
        drv._server.runCmds.side_effect = Exception('server error')

        self.assertRaises(arista.AristaRpcError, drv.get_network_list)


class AristaOVSDriverTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_rpc = mock.MagicMock()
        self.drv = arista.AristaDriver(self.fake_rpc)

    def tearDown(self):
        pass

    def test_no_rpc_call_on_delete_network_if_it_was_not_provisioned(self):
        network_id = 'net1-id'

        self.fake_rpc.get_network_list.return_value = {}
        self.drv.delete_network(network_id)

        self.fake_rpc.get_network_list.assert_called_once_with()

    def test_deletes_network_if_it_was_provisioned_before(self):
        network_id = 'net1-id'

        self.fake_rpc.delete_network(network_id)

        self.drv.create_network(network_id)
        self.drv.delete_network(network_id)

        self.fake_rpc.delete_network.assert_called_once_with(network_id)

    def test_rpc_request_not_sent_for_non_existing_host_unplug(self):
        network_id = 'net1-id'
        vlan_id = 123
        host_id = 'ubuntu123'

        self.drv.create_network(network_id)
        self.drv.unplug_host(network_id, vlan_id, host_id)

    def test_rpc_request_sent_for_existing_vlan_on_unplug_host(self):
        network_id = 'net1-id'
        vlan_id = 1234
        host1_id = 'ubuntu1'
        host2_id = 'ubuntu2'

        self.drv.create_network(network_id)

        self.drv.plug_host(network_id, vlan_id, host1_id)
        self.drv.plug_host(network_id, vlan_id, host2_id)
        self.drv.unplug_host(network_id, vlan_id, host2_id)
        self.drv.unplug_host(network_id, vlan_id, host1_id)

        expected_plugs = [(network_id, vlan_id, host1_id),
                          (network_id, vlan_id, host2_id)]
        expected_unplugs = [(network_id, vlan_id, host2_id),
                            (network_id, vlan_id, host1_id)]

        self.fake_rpc.plug_host_into_vlan.call_arg_list = expected_plugs
        self.fake_rpc.unplug_host_from_vlan.call_arg_list = expected_unplugs

    def test_rpc_request_not_sent_for_existing_vlan_after_plug_host(self):
        network_id = 'net1-id'
        vlan_id = 1001
        host_id = 'ubuntu1'

        # Common use-case:
        #   1. User creates network - quantum net-create net1
        #   2. Boots 3 VMs connected to previously created quantum network
        #      'net1', and VMs are scheduled on the same hypervisor
        # In this case RPC request must be sent only once
        self.drv.create_network(network_id)

        self.drv.plug_host(network_id, vlan_id, host_id)
        self.drv.plug_host(network_id, vlan_id, host_id)
        self.drv.plug_host(network_id, vlan_id, host_id)

        self.fake_rpc.plug_host_into_vlan(network_id, vlan_id, host_id)

    def test_rpc_request_not_sent_for_existing_vlan_after_start(self):
        seg_type = driver_api.VLAN_SEGMENTATION
        net1_id = 'net1-id'
        net2_id = 'net2-id'
        net2_vlan = 1002
        net2_host = 'ubuntu3'
        provisioned_networks = {net1_id: {'hostId': ['ubuntu1'],
                                          'name': net1_id,
                                          'segmentationId': 1000,
                                          'segmentationType': seg_type},
                                net2_id: {'hostId': ['ubuntu2', net2_host],
                                          'name': net2_id,
                                          'segmentationId': net2_vlan,
                                          'segmentationType': seg_type}}

        network_id = net2_id
        segmentation_id = net2_vlan
        host_id = net2_host

        fake_rpc = mock.MagicMock()
        fake_rpc.get_network_list.return_value = provisioned_networks

        drv = arista.AristaDriver(fake_rpc)
        drv.create_network(network_id)

        # wrapper.plug_host_into_vlan() should not be called in this case
        drv.plug_host(network_id, segmentation_id, host_id)

    def test_rpc_brocker_method_is_called(self):
        network_id = 123
        vlan_id = 123
        host_id = 123

        self.fake_rpc.plug_host_into_vlan(network_id, vlan_id, host_id)

        self.drv.plug_host(network_id, vlan_id, host_id)
