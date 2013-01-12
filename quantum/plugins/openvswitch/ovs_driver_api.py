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

"""
Generic API within OVS driver. Allows for insertion of different backends
to be used for L2 network connectivity.

See: https://mirantis.jira.com/wiki/display/ARISTA/Full+specification
TODO: Move link to globally-accessed place (launchpad.net)
"""


from abc import ABCMeta, abstractmethod


VLAN_SEGREGATION = 'vlan'
TUNNEL_SEGREGATION = 'tunnel'


class OVSDriverAPI(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def create_tenant_network(self, context, network_id, segmentation_type):
        """
        Configures isolated L2 segment for a given tenant using :param
        segmentation_type:.

        :param context: quantum API request context
        :param network_id: globally-unique quantum network identifier
        :param segmentation_type: either VLAN or tunnel
        """
        pass

    @abstractmethod
    def plug_host(self, context, network_id, segmentation_type,
                  segmentation_id, host_id):
        """
        Connects L2 network with a compute node
        :param context: quantum API request context
        :param network_id: globally-unique quantum network identifier
        :param segmentation_type: either VLAN or tunnel
        :param segmentation_id: VLAN or tunnel ID
        :param host_id: hypervisor (compute node)
        """
        pass

    @abstractmethod
    def unplug_host(self, context, network_id, segmentation_type,
                    segmentation_id, host_id):
        """
        Removes connection between L2 network segment and a compute node
        :param context: quantum API request context
        :param network_id: globally-unique quantum network identifier
        :param segmentation_type: either VLAN or tunnel
        :param segmentation_id: VLAN or tunnel ID
        :param host_id: hypervisor (compute node)
        """
        pass

    @abstractmethod
    def delete_tenant_network(self, context, network_id):
        """
        Deletes L2 network segment (vlan or tunnel) configuration from the
        hardware
        :param context: quantum API request context
        :param network_id: globally-unique quantum network identifier
        """
        pass

    @abstractmethod
    def get_tenant_network(self, context, networkd_id=None):
        """
        If :param network_id: is not set - returns list of available L2
        networks
        If :param network_id: is set - returns detailed information about the
        network
        :param context: quantum API request context
        :param networkd_id: globally-unique quantum network identifier
        """
        pass
