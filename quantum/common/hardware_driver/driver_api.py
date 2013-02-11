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

"""Generic API for hardware backend driver.

Allows for insertion of different backends to be used for L2 network
connectivity. May be used for any quantum plugin which supports portbindings
extension.

https://blueprints.launchpad.net/quantum/+spec/ovsplugin-hardware-devices
"""

import abc


VLAN_SEGMENTATION = 'vlan'


class HardwareDriverAPI(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create_network(self, network_id):
        """Configures isolated L2 segment for a given network.

        :param network_id: globally-unique quantum network identifier
        :param segmentation_type: either VLAN or tunnel
        """
        pass

    @abc.abstractmethod
    def plug_host(self, network_id, segmentation_id, host_id):
        """Adds host into the network.

        :param network_id: globally-unique quantum network identifier
        :param segmentation_id: VLAN or tunnel ID
        :param host_id: hypervisor (compute node)
        """
        pass

    @abc.abstractmethod
    def unplug_host(self, network_id, segmentation_id, host_id):
        """Removes connection between L2 network segment and a compute node.

        :param network_id: globally-unique quantum network identifier
        :param segmentation_id: VLAN or tunnel ID
        :param host_id: hypervisor (compute node)
        """
        pass

    @abc.abstractmethod
    def delete_network(self, network_id):
        """Deletes L2 network segment configuration from the hardware.

        :param context: quantum API request context
        :param network_id: globally-unique quantum network identifier
        """
        pass
