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

import mock

from heat.engine.clients.os import nova
from heat.engine.resources.openstack.nova import host_aggregate
from heat.engine import stack
from heat.engine import template
from heat.tests import common
from heat.tests import utils

AGGREGATE_TEMPLATE = {
    'heat_template_version': '2013-05-23',
    'description':  'Heat Aggregate creation example',
    'resources': {
        'my_aggregate': {
            'type': 'OS::Nova::HostAggregate',
            'properties': {
                'name': 'host_aggregate',
                'availability_zone': 'nova',
                'hosts': ['host_1', 'host_2'],
                'metadata': {"availability_zone": "nova"}
            }
        }
    }
}


class NovaHostAggregateTest(common.HeatTestCase):
    def setUp(self):
        super(NovaHostAggregateTest, self).setUp()
        self.patchobject(nova.NovaClientPlugin,
                         'has_extension',
                         return_value=True)
        self.ctx = utils.dummy_context()

        self.stack = stack.Stack(
            self.ctx, 'nova_aggregate_test_stack',
            template.Template(AGGREGATE_TEMPLATE)
        )

        self.my_aggregate = self.stack['my_aggregate']
        nova_client = mock.MagicMock()
        self.novaclient = mock.MagicMock()
        self.my_aggregate.client = nova_client
        nova_client.return_value = self.novaclient
        self.aggregates = self.novaclient.aggregates

    def test_resource_mapping(self):
        mapping = host_aggregate.resource_mapping()
        self.assertEqual(1, len(mapping))
        self.assertEqual(host_aggregate.HostAggregate,
                         mapping['OS::Nova::HostAggregate'])
        self.assertIsInstance(self.my_aggregate,
                              host_aggregate.HostAggregate)

    def test_aggregate_handle_create(self):
        value = mock.MagicMock()
        aggregate_id = '927202df-1afb-497f-8368-9c2d2f26e5db'
        value.id = aggregate_id
        self.aggregates.create.return_value = value
        self.my_aggregate.handle_create()
        value.set_metadata.assert_called_once_with(
            {"availability_zone": "nova"})
        self.assertEqual(2, value.add_host.call_count)
        self.assertEqual(aggregate_id, self.my_aggregate.resource_id)

    def test_aggregate_handle_update_name(self):
        value = mock.MagicMock()
        self.aggregates.get.return_value = value
        prop_diff = {'name': 'new_host_aggregate',
                     "availability_zone": "new_nova"}
        expected = {'name': 'new_host_aggregate',
                    "availability_zone": "new_nova"}
        self.my_aggregate.handle_update(
            json_snippet=None, tmpl_diff=None, prop_diff=prop_diff
        )
        value.update.assert_called_once_with(expected)

    def test_aggregate_handle_update_hosts(self):
        value = mock.MagicMock()
        self.aggregates.get.return_value = value
        prop_diff = {'hosts': ['host_1', 'host_3']}
        add_host_expected = 'host_3'
        remove_host_expected = 'host_2'
        self.my_aggregate.handle_update(
            json_snippet=None, tmpl_diff=None, prop_diff=prop_diff
        )
        self.assertEqual(0, value.update.call_count)
        self.assertEqual(0, value.set_metadata.call_count)
        value.add_host.assert_called_once_with(add_host_expected)
        value.remove_host.assert_called_once_with(remove_host_expected)

    def test_aggregate_handle_update_metadata(self):
        value = mock.MagicMock()
        self.aggregates.get.return_value = value
        prop_diff = {'metadata': {"availability_zone": "nova3"}}
        set_metadata_expected = {"availability_zone": "nova3"}
        self.my_aggregate.handle_update(
            json_snippet=None, tmpl_diff=None, prop_diff=prop_diff
        )
        self.assertEqual(0, value.update.call_count)
        self.assertEqual(0, value.add_host.call_count)
        value.set_metadata.assert_called_once_with(set_metadata_expected)
