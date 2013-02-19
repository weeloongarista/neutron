# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 OpenStack LLC
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
#

"""Added hardware driver support for Arista backend

Revision ID: 3e7e0c0e6540
Revises: 1b693c095aa3
Create Date: 2013-02-13 19:27:33.430833

"""

# revision identifiers, used by Alembic.
revision = '3e7e0c0e6540'
down_revision = '1b693c095aa3'

# Change to ['*'] if this migration applies to all plugins

migration_for_plugins = [
    'quantum.plugins.openvswitch.ovs_quantum_plugin.OVSQuantumPluginV2'
]

from alembic import op
import sqlalchemy as sa

from quantum.db import migration


def upgrade(active_plugin=None, options=None):
    if not migration.should_run(active_plugin, migration_for_plugins):
        return

    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(u'arista_provisioned_nets',
                    sa.Column(u'id', sa.Integer(), nullable=False),
                    sa.Column(u'network_id', sa.String(36), nullable=True),
                    sa.Column(u'segmentation_id', sa.Integer(),
                              autoincrement=False, nullable=True),
                    sa.Column(u'host_id', sa.String(255), nullable=True),
                    sa.PrimaryKeyConstraint(u'id'))
    ### end Alembic commands ###


def downgrade(active_plugin=None, options=None):
    if not migration.should_run(active_plugin, migration_for_plugins):
        return

    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table(u'arista_provisioned_nets')
    ### end Alembic commands ###
