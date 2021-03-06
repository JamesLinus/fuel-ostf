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

import datetime
import logging

import sqlalchemy as sa
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import joinedload, relationship, object_mapper

from fuel_plugin import consts
from fuel_plugin.ostf_adapter import nose_plugin
from fuel_plugin.ostf_adapter.storage import engine
from fuel_plugin.ostf_adapter.storage import fields


LOG = logging.getLogger(__name__)


BASE = declarative_base()


class ClusterState(BASE):
    """Represents clusters currently
    present in the system. Holds info
    about deployment type which is using in
    redeployment process.

    Is linked with TestSetToCluster entity
    that implements many-to-many relationship with
    TestSet.
    """

    __tablename__ = 'cluster_state'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)
    deployment_tags = sa.Column(ARRAY(sa.String(64)))
    release_version = sa.Column(sa.String(64))


class ClusterTestingPattern(BASE):
    """Stores cluster's pattern for testsets and tests."""

    __tablename__ = 'cluster_testing_pattern'

    cluster_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('cluster_state.id'),
        primary_key=True
    )

    test_set_id = sa.Column(
        sa.String(128),
        sa.ForeignKey('test_sets.id'),
        primary_key=True
    )

    tests = sa.Column(ARRAY(sa.String(512)))

    test_set = relationship('TestSet')


class TestSet(BASE):

    __tablename__ = 'test_sets'

    id = sa.Column(sa.String(128), primary_key=True)
    description = sa.Column(sa.String(256))
    test_path = sa.Column(sa.String(256))
    driver = sa.Column(sa.String(128))
    additional_arguments = sa.Column(fields.ListField())
    cleanup_path = sa.Column(sa.String(128))
    meta = sa.Column(fields.JsonField())
    deployment_tags = sa.Column(ARRAY(sa.String(64)))
    test_runs_ordering_priority = sa.Column(sa.Integer)

    # list of test sets that cannot be executed simultaneously
    # with current test set
    exclusive_testsets = sa.Column(ARRAY(sa.String(128)))

    available_since_release = sa.Column(sa.String(64), default="")

    tests = relationship(
        'Test',
        backref='test_set',
        order_by='Test.name',
        cascade='delete'
    )

    @property
    def frontend(self):
        return {'id': self.id, 'name': self.description}

    @classmethod
    def get_test_set(cls, session, test_set):
        return session.query(cls)\
            .filter_by(id=test_set)\
            .first()


class Test(BASE):

    __tablename__ = 'tests'

    id = sa.Column(sa.Integer(), primary_key=True)
    name = sa.Column(sa.String(512))
    title = sa.Column(sa.String(512))
    description = sa.Column(sa.Text())
    duration = sa.Column(sa.String(512))
    message = sa.Column(sa.Text())
    traceback = sa.Column(sa.Text())
    status = sa.Column(sa.Enum(consts.TEST_STATUSES, name='test_states'))
    step = sa.Column(sa.Integer())
    time_taken = sa.Column(sa.Float())
    meta = sa.Column(fields.JsonField())
    deployment_tags = sa.Column(ARRAY(sa.String(64)))
    available_since_release = sa.Column(sa.String(64), default="")

    test_run_id = sa.Column(
        sa.Integer(),
        sa.ForeignKey(
            'test_runs.id',
            ondelete='CASCADE'
        )
    )

    test_set_id = sa.Column(
        sa.String(length=128),
        sa.ForeignKey(
            'test_sets.id',
            ondelete='CASCADE'
        )
    )

    @property
    def frontend(self):
        return {
            'id': self.name,
            'testset': self.test_set_id,
            'name': self.title,
            'description': self.description,
            'duration': self.duration,
            'message': self.message,
            'step': self.step,
            'status': self.status,
            'taken': self.time_taken
        }

    @classmethod
    def add_result(cls, session, test_run_id, test_name, data):
        session.query(cls).\
            filter(cls.name == test_name,
                   cls.test_run_id == test_run_id).\
            update(data, synchronize_session='fetch')

    @classmethod
    def update_running_tests(cls, session, test_run_id,
                             status=consts.TEST_STATUSES.stopped):
        session.query(cls). \
            filter(cls.test_run_id == test_run_id,
                   cls.status.in_(
                       (consts.TEST_STATUSES.running,
                        consts.TEST_STATUSES.wait_running))). \
            update({'status': status}, synchronize_session='fetch')

    @classmethod
    def update_test_run_tests(cls, session, test_run_id,
                              tests_names,
                              status=consts.TEST_STATUSES.wait_running):
        session.query(cls). \
            filter(cls.name.in_(tests_names),
                   cls.test_run_id == test_run_id). \
            update({'status': status, 'time_taken': None},
                   synchronize_session='fetch')

    def copy_test(self, test_run, predefined_tests):
        """Performs copying of tests for newly created
        test_run.
        """
        new_test = self.__class__()
        mapper = object_mapper(self)
        primary_keys = set([col.key for col in mapper.primary_key])
        for column in mapper.iterate_properties:
            if column.key not in primary_keys:
                setattr(new_test, column.key, getattr(self, column.key))
        new_test.test_run_id = test_run.id
        if predefined_tests and new_test.name not in predefined_tests:
            new_test.status = consts.TEST_STATUSES.disabled
        else:
            new_test.status = consts.TEST_STATUSES.wait_running
        return new_test


class TestRun(BASE):

    __tablename__ = 'test_runs'

    id = sa.Column(sa.Integer(), primary_key=True)
    cluster_id = sa.Column(sa.Integer(), nullable=False)
    status = sa.Column(sa.Enum(consts.TESTRUN_STATUSES,
                               name='test_run_states'),
                       nullable=False)
    meta = sa.Column(fields.JsonField())
    started_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
    ended_at = sa.Column(sa.DateTime)
    pid = sa.Column(sa.Integer)

    test_set_id = sa.Column(sa.String(128))
    cluster_id = sa.Column(sa.Integer)

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['test_set_id', 'cluster_id'],
            ['cluster_testing_pattern.test_set_id',
             'cluster_testing_pattern.cluster_id'],
            ondelete='CASCADE'
        ),
        {}
    )

    cluster_testing_pattern = relationship('ClusterTestingPattern')
    test_set = association_proxy(
        'cluster_testing_pattern', 'test_set'
    )

    tests = relationship(
        'Test',
        backref='test_run',
        order_by='Test.name',
        cascade='delete'
    )

    def update(self, status):
        self.status = status
        if status == 'finished':
            self.ended_at = datetime.datetime.utcnow()

    @property
    def enabled_tests(self):
        return [test.name for test
                in self.tests if test.status != consts.TEST_STATUSES.disabled]

    def is_finished(self):
        return self.status == consts.TESTRUN_STATUSES.finished

    @property
    def frontend(self):
        test_run_data = {
            'id': self.id,
            'testset': self.test_set_id,
            'meta': self.meta,
            'cluster_id': self.cluster_id,
            'status': self.status,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'tests': []
        }
        if self.tests:
            test_run_data['tests'] = [test.frontend for test in self.tests]
        return test_run_data

    @classmethod
    def add_test_run(cls, session, test_set, cluster_id,
                     status=consts.TESTRUN_STATUSES.running,
                     tests=None):
        """Creates new test_run object with given data
        and makes copy of tests that will be bound
        with this test_run. Copying is performed by
        copy_test method of Test class.
        """
        predefined_tests = tests or []
        tests_names = session.query(ClusterTestingPattern.tests)\
            .filter_by(test_set_id=test_set, cluster_id=cluster_id)\
            .scalar()

        tests = session.query(Test)\
            .filter(Test.name.in_(tests_names))\
            .filter_by(test_set_id=test_set)\
            .filter_by(test_run_id=None)

        test_run = cls(test_set_id=test_set, cluster_id=cluster_id,
                       status=status)
        session.add(test_run)

        for test in tests:
            new_test = test.copy_test(test_run, predefined_tests)
            session.add(new_test)
            test_run.tests.append(new_test)
            # NOTE(akostrikov) Seems there is a problem with transaction
            # isolation, so we need not only to flush, but also to commit.
            # We fork and then in forks we flush sql items. But it seems that
            # it happens in transaction so we are not getting in other
            # processes add results. So I force transaction commit to provide
            # changes to all forks os OSTF.
            session.commit()
        session.flush()

        return test_run

    @classmethod
    def get_last_test_run(cls, session, test_set, cluster_id):
        test_run = session.query(cls). \
            filter_by(cluster_id=cluster_id, test_set_id=test_set). \
            order_by(desc(cls.id)).first()
        return test_run

    @classmethod
    def get_test_results(cls):
        session = engine.get_session()
        test_runs = session.query(cls). \
            options(joinedload('tests')). \
            order_by(desc(cls.id))
        session.commit()
        session.close()
        return test_runs

    @classmethod
    def get_test_run(cls, session, test_run_id, joined=False):
        if not joined:
            test_run = session.query(cls). \
                filter_by(id=test_run_id).first()
        else:
            test_run = session.query(cls). \
                options(joinedload('tests')). \
                filter_by(id=test_run_id).first()
        return test_run

    @classmethod
    def update_test_run(cls, session, test_run_id, updated_data):
        if updated_data.get('status') in [consts.TESTRUN_STATUSES.finished]:
            updated_data['ended_at'] = datetime.datetime.utcnow()

        session.query(cls). \
            filter(cls.id == test_run_id). \
            update(updated_data, synchronize_session='fetch')

    @classmethod
    def is_last_running(cls, session, test_set, cluster_id):
        """Checks whether there one can perform creation of new
        test_run by testing of existing of test_run object
        with given data or test_run with 'finished' status.
        """
        test_run = cls.get_last_test_run(session, test_set, cluster_id)
        return not bool(test_run) or test_run.is_finished()

    @classmethod
    def start(cls, session, test_set, metadata, tests, dbpath, token=None):
        plugin = nose_plugin.get_plugin(test_set.driver)
        if cls.is_last_running(session, test_set.id,
                               metadata['cluster_id']):

            test_run = cls.add_test_run(
                session, test_set.id,
                metadata['cluster_id'], tests=tests)

            plugin.run(test_run, test_set, dbpath,
                       metadata.get('ostf_os_access_creds'), token=token)

            return test_run.frontend
        return {}

    def restart(self, session, dbpath,
                ostf_os_access_creds, tests=None, token=None):
        """Restart test run with
            if tests given they will be enabled
        """
        if TestRun.is_last_running(session,
                                   self.test_set_id,
                                   self.cluster_id):
            plugin = nose_plugin.get_plugin(self.test_set.driver)

            self.update(consts.TEST_STATUSES.running)
            if tests:
                Test.update_test_run_tests(
                    session, self.id, tests)

            plugin.run(self, self.test_set, dbpath,
                       ostf_os_access_creds, tests, token=token)
            return self.frontend
        return {}

    def stop(self, session):
        """Stop test run if running
        """
        plugin = nose_plugin.get_plugin(self.test_set.driver)
        killed = plugin.kill(self)
        if killed:
            Test.update_running_tests(
                session, self.id, status=consts.TEST_STATUSES.stopped)
        return self.frontend
