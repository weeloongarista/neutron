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

from quantum.common.hardware_driver import driver_api


class DummyDriver(driver_api.HardwareDriverAPI):
    """Empty implementation of HardwareDriverAPI."""

    def create_network(self, network_id):
        pass

    def plug_host(self, network_id, segmentation_id, host_id):
        pass

    def unplug_host(self, network_id, segmentation_id, host_id):
        pass

    def delete_network(self, network_id):
        pass
