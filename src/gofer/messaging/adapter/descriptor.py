import os

from logging import getLogger
from copy import deepcopy as clone

from gofer.config import Config, Graph
from gofer.config import REQUIRED, OPTIONAL, BOOL, ANY, NUMBER
from gofer.config import ValidationException


log = getLogger(__name__)


DEFAULT = {
    'main': {
        'enabled': 'true',
        'priority': 0
    }
}


SCHEMA = (
    ('main', REQUIRED,
        (
            ('enabled', OPTIONAL, BOOL),
            ('package', REQUIRED, ANY),
            ('provides', OPTIONAL, ANY),
            ('priority', OPTIONAL, NUMBER),
        ),
    ),
)


class Descriptor(Graph):
    """
    Adapter descriptor.
    """

    @staticmethod
    def load(path):
        """
        Load all adapter descriptors.
        :param path: The absolute path to a directory containing descriptors.
        :type path: str
        :return: A list of descriptors sorted by priority.
        :rtype: list
        """
        loaded = []
        for name in os.listdir(path):
            _path = os.path.join(path, name)
            if not os.path.isfile(_path):
                continue
            try:
                descriptor = Descriptor(_path)
                loaded.append(descriptor)
            except (OSError, ValidationException):
                log.exception(path)
        return sorted(loaded, key=lambda d: int(d.main.priority))

    def __init__(self, path):
        """
        :param path: The absolute path to a descriptor.
        :type path: str
        """
        base = Config(clone(DEFAULT))
        descriptor = Config(path)
        descriptor.validate(SCHEMA)
        base.update(descriptor)
        Graph.__init__(self, base)
        self.path = path

    @property
    def provides(self):
        return [p.strip() for p in self.main.provides.split(',') if p]
