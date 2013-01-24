# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from quantum.openstack.common import cfg


DEFAULT_BRIDGE_MAPPINGS = []
DEFAULT_VLAN_RANGES = []
DEFAULT_TUNNEL_RANGES = []

ovs_opts = [
    cfg.StrOpt('integration_bridge', default='br-int'),
    cfg.BoolOpt('enable_tunneling', default=False),
    cfg.StrOpt('tunnel_bridge', default='br-tun'),
    cfg.StrOpt('int_peer_patch_port', default='patch-tun',
               help=_("Peer patch port in integration bridge for tunnel "
                      "bridge")),
    cfg.StrOpt('tun_peer_patch_port', default='patch-int',
               help=_("Peer patch port in tunnel bridge for integration "
                      "bridge")),
    cfg.StrOpt('local_ip', default=''),
    cfg.ListOpt('bridge_mappings',
                default=DEFAULT_BRIDGE_MAPPINGS,
                help=_("List of <physical_network>:<bridge>")),
    cfg.StrOpt('tenant_network_type', default='local',
               help=_("Network type for tenant networks "
                      "(local, vlan, gre, or none)")),
    cfg.ListOpt('network_vlan_ranges',
                default=DEFAULT_VLAN_RANGES,
                help=_("List of <physical_network>:<vlan_min>:<vlan_max> "
                       "or <physical_network>")),
    cfg.ListOpt('tunnel_id_ranges',
                default=DEFAULT_TUNNEL_RANGES,
                help=_("List of <tun_min>:<tun_max>")),
]

agent_opts = [
    cfg.IntOpt('polling_interval', default=2),
    cfg.StrOpt('root_helper', default='sudo'),
]

generic_ovs_driver_opts = [
    cfg.StrOpt('ovs_driver',
            default='quantum.plugins.openvswitch.drivers.dummy.DummyOVSDriver',
            help='OVS driver used as a backend.'),
    cfg.StrOpt('ovs_driver_segmentation_type',
            default='vlan',
            help=('L2 segregation type to be used on hardware routers. One of '
                  'vlan or tunnel is supported.'))
]

arista_driver_opts = [
    cfg.StrOpt('arista_eapi_user',
               default=None,
               help='Username for Arista vEOS'),
    cfg.StrOpt('arista_eapi_pass',
               default=None,
               help='Password for Arista vEOS'),
    cfg.StrOpt('arista_eapi_host',
               default=None,
               help='Arista vEOS host IP')
]


cfg.CONF.register_opts(ovs_opts, "OVS")
cfg.CONF.register_opts(agent_opts, "AGENT")
cfg.CONF.register_opts(arista_driver_opts, "OVS_DRIVER")
cfg.CONF.register_opts(generic_ovs_driver_opts, "OVS_DRIVER")
