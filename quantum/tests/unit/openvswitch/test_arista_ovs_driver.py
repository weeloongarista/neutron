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

import jsonrpclib
import mox
import unittest2


from quantum.openstack.common import cfg
from quantum.plugins.openvswitch import ovs_driver_api
from quantum.plugins.openvswitch.drivers import arista


def clear_config():
    cfg.CONF.clear()


def setup_arista_wrapper_config(value=None):
    for opt in arista.AristaRPCWrapper.required_options:
        cfg.CONF.set_override(opt, value, "ARISTA_DRIVER")


class AristaRPCWrapperInvalidConfigTestCase(unittest2.TestCase):
    def setUp(self):
        self.setup_invalid_config()  # Invalid config, required options not set

    def tearDown(self):
        clear_config()

    def setup_invalid_config(self):
        setup_arista_wrapper_config(None)

    def test_raises_exception_on_wrong_configuration(self):
        self.assertRaises(arista.AristaConfigError, arista.AristaRPCWrapper)


class AristaRPCWrapperValidConfigTestCase(unittest2.TestCase):
    def setUp(self):
        self.setup_valid_config()
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()
        clear_config()

    def setup_valid_config(self):
        # Config is not valid if value is not set
        setup_arista_wrapper_config('value')

    def test_no_exception_on_correct_configuration(self):
        obj = arista.AristaRPCWrapper()

        self.assertNotEqual(obj, None)

    def test_plug_host_into_vlan_calls_rpc(self):
        drv = arista.AristaRPCWrapper()

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(mox.IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'
        vlan_id = 123
        host = 'host'
        drv.plug_host_into_vlan(network_id, vlan_id, host)

    def test_unplug_host_from_vlan_calls_rpc(self):
        drv = arista.AristaRPCWrapper()

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(mox.IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'
        vlan_id = 123
        host = 'host'
        drv.unplug_host_from_vlan(network_id, vlan_id, host)

    def test_delete_network_calls_rpc(self):
        drv = arista.AristaRPCWrapper()

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(mox.IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'

        drv.delete_network(network_id)

    def test_get_network_info_returns_none_when_no_such_net(self):
        drv = arista.AristaRPCWrapper()
        unavailable_network_id = '12345'

        self.mocker.StubOutWithMock(drv, 'get_network_list')
        drv.get_network_list().AndReturn([])

        self.mocker.ReplayAll()

        net_info = drv.get_network_info(unavailable_network_id)
        self.assertEqual(net_info, None, ('Network info must be "None"'
                                          'for unknown network'))

    def test_get_network_info_returns_info_for_available_net(self):
        drv = arista.AristaRPCWrapper()
        valid_network_id = '12345'
        valid_net_info = {'network_id': valid_network_id,
                          'some_info': 'net info'}
        known_nets = [valid_net_info]

        self.mocker.StubOutWithMock(drv, 'get_network_list')
        drv.get_network_list().AndReturn(known_nets)

        self.mocker.ReplayAll()

        net_info = drv.get_network_info(valid_network_id)
        self.assertEqual(net_info, valid_net_info,
                         ('Must return network info for a valid net'))

    def test_rpc_is_sent(self):
        fake_net = {'networks': 123}
        cli_ret = [{}, {}, fake_net, {}]

        fake_jsonrpc_server = self.mocker.CreateMockAnything()
        fake_jsonrpc_server.runCmds(cmds=mox.IsA(list)).AndReturn(cli_ret)

        drv = arista.AristaRPCWrapper()
        drv._server = fake_jsonrpc_server

        self.mocker.ReplayAll()

        drv.get_network_list()

    def test_exception_is_raised_on_json_server_error(self):
        fake_jsonrpc_server = self.mocker.CreateMockAnything()
        (fake_jsonrpc_server.runCmds(cmds=mox.IsA(list)).
         AndRaise(jsonrpclib.ProtocolError('server error')))

        drv = arista.AristaRPCWrapper()
        drv._server = fake_jsonrpc_server

        self.mocker.ReplayAll()

        self.assertRaises(arista.AristaRpcError, drv.get_network_list)


class AristaOVSDriverTestCase(unittest2.TestCase):
    def setUp(self):
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()

    def test_no_rpc_call_on_delete_network_if_it_was_not_provisioned(self):
        network_id = 'net1-id'

        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)
        fake_rpc.get_network_list().AndReturn({})

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)
        drv.delete_tenant_network(network_id)

    def test_deletes_network_if_it_was_provisioned_before(self):
        network_id = 'net1-id'

        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)
        fake_rpc.get_network_list().AndReturn({})
        fake_rpc.delete_network(network_id)

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)
        drv.create_tenant_network(network_id)
        drv.delete_tenant_network(network_id)

    def test_rpc_request_not_sent_for_non_existing_host_unplug(self):
        network_id = 'net1-id'
        vlan_id = 123
        host_id = 'ubuntu123'

        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)
        fake_rpc.get_network_list().AndReturn({})

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)
        drv.create_tenant_network(network_id)
        drv.unplug_host(network_id, vlan_id, host_id)

    def test_rpc_request_sent_for_existing_vlan_on_unplug_host(self):
        network_id = 'net1-id'
        vlan_id = 1234
        host1_id = 'ubuntu1'
        host2_id = 'ubuntu2'

        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)
        fake_rpc.get_network_list().AndReturn({})
        fake_rpc.plug_host_into_vlan(network_id, vlan_id, host1_id)
        fake_rpc.plug_host_into_vlan(network_id, vlan_id, host2_id)
        fake_rpc.unplug_host_from_vlan(network_id, vlan_id, host2_id)
        fake_rpc.unplug_host_from_vlan(network_id, vlan_id, host1_id)

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)
        drv.create_tenant_network(network_id)

        drv.plug_host(network_id, vlan_id, host1_id)
        drv.plug_host(network_id, vlan_id, host2_id)
        drv.unplug_host(network_id, vlan_id, host2_id)
        drv.unplug_host(network_id, vlan_id, host1_id)

    def test_rpc_request_not_sent_for_existing_vlan_after_plug_host(self):
        network_id = 'net1-id'
        vlan_id = 1001
        host_id = 'ubuntu1'

        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)
        fake_rpc.get_network_list().AndReturn({})
        fake_rpc.plug_host_into_vlan(network_id, vlan_id, host_id)

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)

        # Common use-case:
        #   1. User creates network - quantum net-create net1
        #   2. Boots 3 VMs connected to previously created quantum network
        #      'net1', and VMs are scheduled on the same hypervisor
        # In this case RPC request must be sent only once
        drv.create_tenant_network(network_id)

        drv.plug_host(network_id, vlan_id, host_id)
        drv.plug_host(network_id, vlan_id, host_id)
        drv.plug_host(network_id, vlan_id, host_id)

    def test_rpc_request_not_sent_for_existing_vlan_after_start(self):
        fake_rpc = self.mocker.CreateMock(arista.AristaRPCWrapper)

        seg_type = ovs_driver_api.VLAN_SEGMENTATION
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

        fake_rpc.get_network_list().AndReturn(provisioned_networks)

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc)
        drv.create_tenant_network(network_id)

        # wrapper.plug_host_into_vlan() should not be called in this case
        drv.plug_host(network_id, segmentation_id, host_id)

    def test_rpc_brocker_method_is_called(self):
        fake_rpc_broker = self.mocker.CreateMock(arista.AristaRPCWrapper)

        network_id = 123
        vlan_id = 123
        host_id = 123

        fake_rpc_broker.get_network_list().AndReturn({})
        fake_rpc_broker.plug_host_into_vlan(network_id, vlan_id, host_id)

        self.mocker.ReplayAll()

        drv = arista.AristaOVSDriver(fake_rpc_broker)

        drv.plug_host(network_id, vlan_id, host_id)
