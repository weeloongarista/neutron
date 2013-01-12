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
from quantum.openstack.common import cfg
from quantum.openstack.common import importutils
from quantum.plugins.openvswitch import ovs_db_v2
from quantum.plugins.openvswitch.drivers.dummy import DummyOVSDriver
from quantum.plugins.openvswitch.ovs_driver_api import VLAN_SEGREGATION


class OVSDriverAdapter(object):
    """
    Adapts OVS driver API to OVS plugin incoming arguments.
    """

    # TODO: Refactor to remove 'if not self.driver_available:' check in the
    #       beginning of each method (wrapper?).
    required_options = ['ovs_driver_segmentation_type', 'ovs_driver']
    driver_available = False
    segmentation_type = VLAN_SEGREGATION

    def __init__(self):
        for opt in self.required_options:
            if opt not in cfg.CONF.OVS_DRIVER:
                raise QuantumException('Required option %s is not set' % opt)

        self.segmentation_type = cfg.CONF.OVS_DRIVER[
                                            'ovs_driver_segmentation_type']
        ovs_driver_class = importutils.import_class(
                                            cfg.CONF.OVS_DRIVER['ovs_driver'])
        self._driver = ovs_driver_class()

        OVSDriverAdapter.driver_available = (ovs_driver_class is
                                             not DummyOVSDriver)

    def on_port_create(self, context, port):
        if not self.driver_available:
            return

        p = port['port']

        network_id = p['network_id']
        binding = ovs_db_v2.get_network_binding(None, network_id)
        segmentation_id = binding.segmentation_id
        hypervisor = p['hostname']

        self._driver.plug_host(context, network_id, self.segmentation_type,
                               segmentation_id, hypervisor)

    def on_port_delete(self):
        pass

    def on_port_update(self):
        pass

    def on_network_create(self, context, network):
        if not self.driver_available:
            return

        self._driver.create_tenant_network(context, network['id'],
                                           self.segmentation_type)

    def on_network_update(self, context, network_id):
        if not self.driver_available:
            return
        # TODO: analize what has changed and then act appropriately

    def on_network_delete(self, context, network_id):
        if not self.driver_available:
            return

        self._driver.delete_tenant_network(context, network_id)
