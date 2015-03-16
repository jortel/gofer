from time import sleep
from logging import getLogger

from gofer import Thread
from gofer.messaging.adapter.reliability import YEAR


DELAY = 10
MAX_DELAY = 90
RETRIES = YEAR / MAX_DELAY
DELAY_MULTIPLIER = 1.2


log = getLogger(__name__)


def retry(*exception):
    def _fn(fn):
        def inner(connection):
            if connection.retry:
                retries = RETRIES
            else:
                retries = 0
            delay = DELAY
            url = connection.url
            while not Thread.aborted():
                try:
                    log.info('connecting: %s', url)
                    impl = fn(connection)
                    log.info('connected: %s', url)
                    return impl
                except exception, e:
                    log.error('connect: %s, failed: %s', url, e)
                    if retries > 0:
                        log.info('retry in %d seconds', delay)
                        sleep(delay)
                        if delay < MAX_DELAY:
                            delay *= DELAY_MULTIPLIER
                        retries -= 1
                    else:
                        raise
        return inner
    return _fn
