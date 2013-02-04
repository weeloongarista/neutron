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
from quantum.plugins.openvswitch.drivers.arista import AristaConfigError
from quantum.plugins.openvswitch.drivers.arista import AristaOVSDriver
from quantum.plugins.openvswitch.drivers.arista import AristaRPCWrapper
from quantum.plugins.openvswitch.drivers.arista import AristaRpcError
from quantum.plugins.openvswitch.ovs_driver_api import VLAN_SEGMENTATION
import jsonrpclib
import mox
import unittest
from quantum.plugins.openvswitch.drivers.arista import ProvisionedVlansStorage


class FakeConfig(object):
    def __init__(self, initial_value=None):
        required_options = AristaRPCWrapper.required_options
        # make compatible with python<=2.6
        self._opts = dict([(opt, initial_value) for opt in required_options])

    def get(self, item):
        return self[item]

    def __getattr__(self, attr):
        return self[attr]

    def __getitem__(self, item):
        return self._opts[item]


class AristaProvisionedVlansStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.drv = ProvisionedVlansStorage()
        self.drv.initialize()
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()
        self.drv.tear_down()

    def test_network_is_remembered(self):
        network_id = '123'
        segmentation_id = 456
        host_id = 'host123'

        self.drv.remember_host(network_id, segmentation_id, host_id)
        net_provisioned = self.drv.is_network_provisioned(network_id)
        self.assertTrue(net_provisioned, 'Network must be provisioned')

    def test_network_is_removed(self):
        network_id = '123'

        self.drv.remember_network(network_id)
        self.drv.forget_network(network_id)

        net_provisioned = self.drv.is_network_provisioned(network_id)

        self.assertFalse(net_provisioned, 'The network should be deleted')

    def test_remembers_multiple_networks(self):
        expected_num_nets = 100
        nets = ['id%s' % n for n in range(expected_num_nets)]
        for net_id in nets:
            self.drv.remember_network(net_id)
            self.drv.remember_host(net_id, 123, 'host')

        num_nets_provisioned = len(self.drv.get_all())

        self.assertEqual(expected_num_nets, num_nets_provisioned,
                         'There should be %(expected_num_nets)d '
                         'nets, not %(num_nets_provisioned)d' % locals())

    def test_removes_all_networks(self):
        num_nets = 100
        nets = ['id%s' % n for n in range(num_nets)]
        host_id = 'host123'
        for net_id in nets:
            self.drv.remember_network(net_id)
            self.drv.remember_host(net_id, 123, host_id)
            self.drv.forget_host(net_id, host_id)

        num_nets_provisioned = self.drv.num_nets_provisioned()
        expected = 0

        self.assertEqual(expected, num_nets_provisioned,
                         'There should be %(expected)d '
                         'nets, not %(num_nets_provisioned)d' % locals())

    def test_network_is_not_deleted_on_forget_host(self):
        network_id = '123'
        vlan_id = 123
        host1_id = 'host1'
        host2_id = 'host2'

        self.drv.remember_network(network_id)
        self.drv.remember_host(network_id, vlan_id, host1_id)
        self.drv.remember_host(network_id, vlan_id, host2_id)
        self.drv.forget_host(network_id, host2_id)

        net_provisioned = (self.drv.is_network_provisioned(network_id) and
                           self.drv.is_network_provisioned(network_id,
                                                           vlan_id,
                                                           host1_id))

        self.assertTrue(net_provisioned, 'The network should not be deleted')

    def test_net_is_not_stored_on_delete(self):
        network_id = '123'
        vlan_id = 123
        removed_host = 'removed_host'
        avail_host = 'available_host'

        self.drv.remember_network(network_id)
        self.drv.remember_host(network_id, vlan_id, removed_host)
        self.drv.remember_host(network_id, vlan_id, avail_host)
        self.drv.forget_host(network_id, removed_host)

        network_is_available = self.drv.is_network_provisioned(network_id)
        removed_host_is_available = self.drv.is_network_provisioned(
                                                           network_id,
                                                           vlan_id,
                                                           removed_host)

        self.assertTrue(network_is_available,
                        'The network should stay available')
        self.assertFalse(removed_host_is_available,
                        '%(removed_host)s should not be available' % locals())

    def test_num_networks_is_valid(self):
        network_id = '123'
        vlan_id = 123
        host1_id = 'host1'
        host2_id = 'host2'
        host3_id = 'host3'

        self.drv.remember_network(network_id)
        self.drv.remember_host(network_id, vlan_id, host1_id)
        self.drv.remember_host(network_id, vlan_id, host2_id)
        self.drv.remember_host(network_id, vlan_id, host3_id)
        self.drv.forget_host(network_id, host2_id)

        num_nets = len(self.drv.get_all_vlans_for_net(network_id))
        expected = 2

        self.assertEqual(expected, num_nets,
                         'There should be %(expected)d records, '
                         'got %(num_nets)d records' % locals())


class AristaRPCWrapperTestCase(unittest.TestCase):
    def setUp(self):
        self.mocker = mox.Mox()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()

    def test_raises_exception_on_wrong_configuration(self):
        invalid_config = FakeConfig()
        self.assertRaises(AristaConfigError, AristaRPCWrapper,
                          invalid_config)

    def test_no_exception_on_correct_configuration(self):
        valid_config = FakeConfig('some_value')

        obj = AristaRPCWrapper(valid_config)

        self.assertNotEqual(obj, None)

    def test_plug_host_into_vlan_calls_rpc(self):
        fake_config = FakeConfig('some_value')

        drv = AristaRPCWrapper(fake_config)

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'
        vlan_id = 123
        host = 'host'
        drv.plug_host_into_vlan(network_id, vlan_id, host)

    def test_unplug_host_from_vlan_calls_rpc(self):
        fake_config = FakeConfig('some_value')

        drv = AristaRPCWrapper(fake_config)

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'
        vlan_id = 123
        host = 'host'
        drv.unplug_host_from_vlan(network_id, vlan_id, host)

    def test_delete_network_calls_rpc(self):
        fake_config = FakeConfig('some_value')

        drv = AristaRPCWrapper(fake_config)

        self.mocker.StubOutWithMock(drv, '_run_openstack_cmd')
        drv._run_openstack_cmd(IsA(list))

        self.mocker.ReplayAll()

        network_id = 'net-id'

        drv.delete_network(network_id)

    def test_get_network_info_returns_none_when_no_such_net(self):
        fake_config = FakeConfig('some_value')
        drv = AristaRPCWrapper(fake_config)
        unavailable_network_id = '12345'

        self.mocker.StubOutWithMock(drv, 'get_network_list')
        drv.get_network_list().AndReturn([])

        self.mocker.ReplayAll()

        net_info = drv.get_network_info(unavailable_network_id)
        self.assertEqual(net_info, None, ('Network info must be "None"'
                                          'for unknown network'))

    def test_get_network_info_returns_info_for_available_net(self):
        fake_config = FakeConfig('some_value')
        drv = AristaRPCWrapper(fake_config)
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
        fake_config = FakeConfig('some_value')
        fake_net = {'networks': 123}
        cli_ret = [{}, {}, fake_net, {}]

        fake_jsonrpc_server = self.mocker.CreateMockAnything()
        fake_jsonrpc_server.runCli(cmds=IsA(list)).AndReturn(cli_ret)

        drv = AristaRPCWrapper(fake_config)
        drv._server = fake_jsonrpc_server

        self.mocker.ReplayAll()

        drv.get_network_list()

    def test_exception_is_raised_on_json_server_error(self):
        fake_config = FakeConfig('some_value')

        fake_jsonrpc_server = self.mocker.CreateMockAnything()
        fake_jsonrpc_server.runCli(cmds=IsA(list)).\
                            AndRaise(jsonrpclib.ProtocolError('server error'))

        drv = AristaRPCWrapper(fake_config)
        drv._server = fake_jsonrpc_server

        self.mocker.ReplayAll()

        self.assertRaises(AristaRpcError, drv.get_network_list)


class AristaOVSDriverTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_conf = {'ovs_driver_segmentation_type': VLAN_SEGMENTATION}

        self.mocker = mox.Mox()
        self.rpc_mock = self.mocker.CreateMock(AristaRPCWrapper)
        self.net_storage_mock = self.mocker.CreateMock(ProvisionedVlansStorage)
        self.net_storage_mock.initialize()

    def tearDown(self):
        self.mocker.VerifyAll()
        self.mocker.UnsetStubs()

    def test_no_rpc_call_on_delete_network_if_it_was_not_provisioned(self):
        network_id = 'net1-id'

        self.net_storage_mock.is_network_provisioned(network_id).\
                AndReturn(False)
        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                                   self.net_storage_mock)
        drv.delete_tenant_network(network_id)

    def test_deletes_network_if_it_was_provisioned_before(self):
        network_id = 'net1-id'

        self.net_storage_mock.remember_network(network_id)
        self.net_storage_mock.is_network_provisioned(network_id).\
                AndReturn(True)
        self.rpc_mock.delete_network(network_id)
        self.net_storage_mock.forget_network(network_id)

        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                              self.net_storage_mock)

        drv.create_tenant_network(network_id)
        drv.delete_tenant_network(network_id)

    def test_rpc_request_not_sent_for_non_existing_host_unplug(self):
        network_id = 'net1-id'
        vlan_id = 123
        host_id = 'ubuntu123'

        self.net_storage_mock.remember_network(network_id)
        self.net_storage_mock.is_network_provisioned(network_id,
                                                     vlan_id,
                                                     host_id).AndReturn(False)

        self.mocker.ReplayAll()
        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                              self.net_storage_mock)

        drv.create_tenant_network(network_id)
        drv.unplug_host(network_id, vlan_id, host_id)

    def test_rpc_request_sent_for_existing_vlan_on_unplug_host(self):
        network_id = 'net1-id'
        vlan_id = 1234
        host1_id = 'ubuntu1'
        host2_id = 'ubuntu2'

        self.rpc_mock.get_network_list().AndReturn({})
        self.rpc_mock.plug_host_into_vlan(network_id, vlan_id, host1_id)
        self.rpc_mock.plug_host_into_vlan(network_id, vlan_id, host2_id)
        self.rpc_mock.unplug_host_from_vlan(network_id, vlan_id, host2_id)
        self.rpc_mock.unplug_host_from_vlan(network_id, vlan_id, host1_id)

        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                              self.net_storage_mock)

        drv.create_tenant_network(network_id)

        drv.plug_host(network_id, vlan_id, host1_id)
        drv.plug_host(network_id, vlan_id, host2_id)
        drv.unplug_host(network_id, vlan_id, host2_id)
        drv.unplug_host(network_id, vlan_id, host1_id)

    def test_rpc_request_not_sent_for_existing_vlan_after_plug_host(self):
        network_id = 'net1-id'
        vlan_id = 1001
        host_id = 'ubuntu1'

        self.rpc_mock.get_network_list().AndReturn({})
        self.rpc_mock.plug_host_into_vlan(network_id, vlan_id, host_id)

        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                              self.net_storage_mock)

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
        seg_type = VLAN_SEGMENTATION
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

        self.rpc_mock.get_network_list().AndReturn(provisioned_networks)

        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                                   self.net_storage_mock)
        drv.create_tenant_network(network_id)

        # wrapper.plug_host_into_vlan() should not be called in this case
        drv.plug_host(network_id, segmentation_id, host_id)

    def test_rpc_brocker_method_is_called(self):
        network_id = 123
        vlan_id = 123
        host_id = 123

        self.rpc_mock.get_network_list().AndReturn({})
        self.rpc_mock.plug_host_into_vlan(network_id, vlan_id, host_id)

        self.mocker.ReplayAll()

        drv = AristaOVSDriver(self.rpc_mock, self.fake_conf,
                                   self.net_storage_mock)
        drv.plug_host(network_id, vlan_id, host_id)
