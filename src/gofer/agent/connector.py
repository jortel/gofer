import os

from logging import getLogger

from gofer.common import mkdir
from gofer.config import Config, get_bool
from gofer.messaging import Connector as ModelConnector
from gofer.messaging import Queue, Exchange
from gofer.rmi.consumer import RequestConsumer
from gofer.pmon import PathMonitor

#
# [connector]
# name = satellite
# url = qpid+amqp://localhost
# authenticator = satellite.agent.authenticator.Authenticator
# ca_certificate = /etc/pki/ca.pem
# client_certificate = /etc/pki/client.pem
# client_key = /etc/pki/key.pem
#
# [model]
# queue = test.queue
#


log = getLogger(__name__)


class Container(object):

    ROOT = '/etc/gofer/connector'

    connectors = {}

    def __init__(self):
        self.path_monitor = PathMonitor()

    def start(self):
        mkdir(Container.ROOT)
        self.path_monitor.add(Container.ROOT, self.changed)
        self.path_monitor.start()
        self.load_all()

    def changed(self, path):
        _dir = Container.ROOT
        if path == _dir:
            listing = [os.path.join(_dir, fn) for fn in os.listdir(_dir)]
            for p in listing:
                if p not in Container.connectors:
                    self.load(path)
        else:
            if os.path.exists(path):
                # reload
                self.unload(path)
                self.load(path)
            else:
                # unload
                self.unload(path)

    def load_all(self):
        _dir = Container.ROOT
        for path in [os.path.join(_dir, fn) for fn in os.listdir(_dir)]:
            try:
                self.load(path)
            except Exception, e:
                log.error(str(e))

    def load(self, path):
        try:
            self._load(path)
        except Exception, e:
            log.error(str(e))

    def _load(self, path):
        descriptor = Config(path).graph()
        # model
        cfg = descriptor.model
        model = Model(cfg.name, cfg.managed)
        model.queue = cfg.queue
        model.expiration = cfg.expiration
        model.exchange = cfg.exchange
        # connector
        cfg = descriptor.connector
        if not get_bool(cfg.enabled):
            # disabled
            return
        connector = ModelConnector(cfg.url)
        connector.ssl.ca_certificate = cfg.ca_certificate
        connector.ssl.client_certificate = cfg.client_certificate
        connector.ssl.client_key = cfg.client_key
        connector.ssl.host_validation = cfg.host_validation
        connector.add()
        connector = Connector(cfg.name, cfg.url, model)
        Container.connectors[path] = connector
        self.path_monitor.add(path, self.changed)

    def unload(self, path):
        try:
            connector = Container.connectors[path]
            connector.stop()
            del Container.connectors[path]
        except KeyError:
            log.warn('%s: not-found', path)


class Model(object):

    def __init__(self, name, managed):
        self.name = name
        self.managed = int(managed)
        self.queue = None
        self.expiration = None
        self.exchange = None

    def setup(self, url):
        """
        Setup the broker model.
        """
        queue = Queue(self.queue)
        if self.managed:
            queue = Queue(self.queue)
            queue.auto_delete = self.expiration > 0
            queue.expiration = self.expiration
            queue.declare(url)
            if self.exchange:
                exchange = Exchange(self.exchange)
                exchange.bind(queue, url)
        return queue

    def teardown(self, url):
        """
        Teardown the broker model.
        """
        if self.managed < 2:
            return
        queue = Queue(self.queue)
        queue.purge(url)
        queue.delete(url)


class Connector(object):

    def __init__(self, name, url, model):
        self.name = name
        self.url = url
        self.model = model
        self.authenticator = None
        self.consumer = None

    def start(self):
        queue = Queue(self.model.queue)
        self.consumer = RequestConsumer(queue, self.url)
        self.consumer.authenticator = self.authenticator
        self.model.setup(self.url)
        self.consumer.start()

    def stop(self):
        self.consumer.stop()
        self.consumer.join()
        self.model.teardown(self.url)
