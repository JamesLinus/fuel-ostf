#    Copyright 2013 Mirantis, Inc.
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

import requests_mock

from fuel_plugin.ostf_adapter import config
from fuel_plugin.ostf_adapter import mixins
from fuel_plugin.testing.tests import base


class TestDeplTagsGetter(base.BaseUnitTest):

    def setUp(self):
        config.init_config([])

    def test_get_cluster_depl_tags(self):
        expected = {
            'cluster_id': 3,
            'attrs': {
                'deployment_tags': set(
                    ['ha', 'rhel', 'additional_components',
                     'murano', 'nova_network', 'public_on_all_nodes',
                     'enable_without_ceph', 'computes_without_dpdk']),
                'release_version': '2015.2-1.0'
            }
        }

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/3',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/3/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/3',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=3',
                           json=cluster['cluster_node'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])

    def test_sriov_deployment_tag(self):
        expected = {
            'cluster_id': 7,
            'attrs': {
                'deployment_tags': set(
                    ['ha', 'rhel', 'additional_components',
                     'murano', 'nova_network', 'public_on_all_nodes',
                     'enable_without_ceph', 'sriov',
                     'computes_without_dpdk']),
                'release_version': '2015.2-1.0'
            }
        }

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/7',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/7/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/7',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=7',
                           json=cluster['cluster_node'])
            m.register_uri('GET', '/api/nodes/1/interfaces',
                           json=cluster['node_interfaces'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])

    def test_dpdk_deployment_tag(self):
        expected = {
            'cluster_id': 8,
            'attrs': {
                'deployment_tags': set(
                    ['computes_with_dpdk', 'neutron', 'enable_without_ceph',
                     'ha', 'public_on_all_nodes', 'rhel',
                     'computes_without_dpdk']),
                'release_version': '2015.2-1.0'
            }
        }

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/8',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/8/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/8',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=8',
                           json=cluster['cluster_node'])
            m.register_uri('GET', '/api/nodes/1/interfaces',
                           json=cluster['node-1_interfaces'])
            m.register_uri('GET', '/api/nodes/2/interfaces',
                           json=cluster['node-2_interfaces'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])


class TestDeplMuranoTags(base.BaseUnitTest):

    def setUp(self):
        config.init_config([])

        self.expected = {
            'attrs': {
                'deployment_tags': set(
                    ['multinode', 'ubuntu', 'additional_components',
                     'nova_network', 'public_on_all_nodes',
                     'enable_without_ceph', 'computes_without_dpdk']),
                'release_version': '2016.1-9.0'
            }
        }

    def test_get_murano_plugin_tags_with_artifacts(self):
        expected = self.expected
        expected['cluster_id'] = 9
        expected['attrs']['deployment_tags'].add('murano_plugin')
        expected['attrs']['deployment_tags'].add('murano_use_glare')

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/9',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/9/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/9',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=9',
                           json=cluster['cluster_node'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])

    def test_get_murano_plugin_tags_without_artifacts(self):
        expected = self.expected
        expected['cluster_id'] = 10
        expected['attrs']['deployment_tags'].add('murano_plugin')
        expected['attrs']['deployment_tags'].add('murano_without_glare')

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/10',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/10/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/10',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=10',
                           json=cluster['cluster_node'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])

    def test_get_murano_tags_with_artifacts(self):
        expected = self.expected
        expected['cluster_id'] = 11
        expected['attrs']['deployment_tags'].add('murano')
        expected['attrs']['deployment_tags'].add('murano_use_glare')

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/11',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/11/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/11',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=11',
                           json=cluster['cluster_node'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])

    def test_get_murano_tags_without_artifacts(self):
        expected = self.expected
        expected['cluster_id'] = 12
        expected['attrs']['deployment_tags'].add('murano')
        expected['attrs']['deployment_tags'].add('murano_without_glare')

        with requests_mock.Mocker() as m:
            cluster = base.CLUSTERS[expected['cluster_id']]
            m.register_uri('GET', '/api/clusters/12',
                           json=cluster['cluster_meta'])
            m.register_uri('GET', '/api/clusters/12/attributes',
                           json=cluster['cluster_attributes'])
            m.register_uri('GET', '/api/releases/12',
                           json=cluster['release_data'])
            m.register_uri('GET', '/api/nodes?cluster_id=12',
                           json=cluster['cluster_node'])
            res = mixins._get_cluster_attrs(expected['cluster_id'])

        self.assertEqual(res, expected['attrs'])
