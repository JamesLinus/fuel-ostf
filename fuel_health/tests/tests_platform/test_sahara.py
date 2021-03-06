# Copyright 2013 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from fuel_health.common.utils.data_utils import rand_name
from fuel_health import saharamanager

LOG = logging.getLogger(__name__)


class SaharaClusterTest(saharamanager.SaharaTestsManager):
    _plugin_name = 'An unknown plugin name'
    _hadoop_version = 'An unknown Hadoop version'
    _worker_processes = 'An unknown list of worker processes'
    _master_processes = 'An unknown list of master processes'

    def setUp(self):
        super(SaharaClusterTest, self).setUp()

        doc_link = 'https://www.fuel-infra.org/#fueldocs'

        max_free_ram_mb = (
            self.get_max_free_compute_node_ram(self.min_required_ram_mb))
        if max_free_ram_mb < self.min_required_ram_mb:
            msg = ('This test requires more hardware resources of your '
                   'OpenStack cluster: at least one of the compute nodes '
                   'must have >= {0} MB of free RAM, but you have only '
                   '{1} MB on most appropriate compute node.'
                   .format(self.min_required_ram_mb, max_free_ram_mb))
            LOG.debug(msg)
            self.skipTest(msg)

        self.image_id = self.find_and_check_image(self._plugin_name,
                                                  self._hadoop_version)
        if not self.image_id:
            msg = ('Sahara image was not correctly registered or it was not '
                   'uploaded at all. Please refer to the Fuel '
                   'documentation ({0}) to find out how to upload and/or '
                   'register image for Sahara.'.format(doc_link))
            LOG.debug(msg)
            self.skipTest(msg)

        flavor_id = self.create_flavor()
        private_net_id, floating_ip_pool = self.create_network_resources()
        self.cl_template = {
            'name': rand_name('sahara-cluster-template-'),
            'plugin': self._plugin_name,
            'hadoop_version': self._hadoop_version,
            'node_groups': [
                {
                    'name': 'master',
                    'flavor_id': flavor_id,
                    'node_processes': self._master_processes,
                    'floating_ip_pool': floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'worker',
                    'flavor_id': flavor_id,
                    'node_processes': self._worker_processes,
                    'floating_ip_pool': floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                }
            ],
            'net_id': private_net_id,
            'cluster_configs': {'HDFS': {'dfs.replication': 1}},
            'description': 'Test cluster template'
        }
        self.cluster = {
            'name': rand_name('sahara-cluster-'),
            'plugin': self._plugin_name,
            'hadoop_version': self._hadoop_version,
            'default_image_id': self.image_id,
            'description': 'Test cluster'
        }


class VanillaTwoClusterTest(SaharaClusterTest):
    def setUp(self):
        mapping_versions_of_plugin = {
            "6.1": "2.4.1",
            "7.0": "2.6.0",
            "8.0": "2.7.1",
            "9.0": "2.7.1",
            "9.1": "2.7.1",
            "10.0": "2.7.1"
        }
        self._plugin_name = 'vanilla'
        self._hadoop_version = mapping_versions_of_plugin.get(
            self.config.fuel.fuel_version, "2.7.1")
        self._worker_processes = ['nodemanager', 'datanode']
        self._master_processes = ['resourcemanager', 'namenode', 'oozie',
                                  'historyserver', 'secondarynamenode']
        super(VanillaTwoClusterTest, self).setUp()

        self.processes_map = {
            'resourcemanager': [8032, 8088],
            'namenode': [9000, 50070],
            'nodemanager': [8042],
            'datanode': [50010, 50020, 50075],
            'secondarynamenode': [50090],
            'oozie': [11000],
            'historyserver': [19888]
        }

    def test_vanilla_two_cluster(self):
        """Sahara test for launching a simple Vanilla2 cluster
        Target component: Sahara

        Scenario:
            1. Create a cluster template
            2. Create a cluster
            3. Wait for the cluster to build and get to "Active" status
            4. Check deployment of Hadoop services on the cluster
            5. Check ability to log into cluster nodes via SSH
            6. Delete the cluster
            7. Delete the cluster template

        Duration:  1200 s.
        Available since release: 2014.2-6.1
        Deployment tags: Sahara
        """

        fail_msg = 'Failed to create cluster template.'
        msg = 'creating cluster template'
        cl_template_id = self.verify(30, self.create_cluster_template,
                                     1, fail_msg, msg, **self.cl_template)

        self.cluster['cluster_template_id'] = cl_template_id
        fail_msg = 'Failed to create cluster.'
        msg = 'creating cluster'
        cluster_id = self.verify(30, self.create_cluster, 2,
                                 fail_msg, msg, **self.cluster)

        fail_msg = 'Failed while polling cluster status.'
        msg = 'polling cluster status'
        self.verify(self.cluster_timeout,
                    self.poll_cluster_status, 3, fail_msg, msg, cluster_id)

        fail_msg = 'Failed to check deployment of Hadoop services on cluster.'
        msg = 'checking deployment of Hadoop services on cluster'
        self.verify(self.process_timeout, self.check_hadoop_services,
                    4, fail_msg, msg, cluster_id, self.processes_map)

        fail_msg = 'Failed to log into cluster nodes via SSH.'
        msg = 'logging into cluster nodes via SSH'
        self.verify(
            30, self.check_node_access_via_ssh, 5, fail_msg, msg, cluster_id)

        fail_msg = 'Failed to delete cluster.'
        msg = 'deleting cluster'
        self.verify(self.delete_timeout, self.delete_resource, 6,
                    fail_msg, msg, self.sahara_client.clusters, cluster_id)

        fail_msg = 'Failed to delete cluster template.'
        msg = 'deleting cluster template'
        self.verify(30, self.delete_resource, 7, fail_msg, msg,
                    self.sahara_client.cluster_templates, cl_template_id)
