
import os
import sys
import tempfile
import json
import time
import shutil

srcdir = os.path.abspath(os.path.dirname(__file__)) + '/../../src/'
sys.path.insert(0, srcdir)

from unittest import TestCase
from mock import Mock
from gofer.messaging import Envelope
from gofer.messaging.producer import Producer
from gofer.messaging.consumer import Consumer
from gofer.rmi import async
from gofer.rmi.async import WatchDog, Journal, ReplyConsumer

SN = '123'
REPLYTO = 'xyz'
ANY = {'1':2}
NOW = time.time()
ELAPSED = 0

def now():
    return NOW+ELAPSED


class TestWatchDog(TestCase):
    
    def setUp(self):
        global ELAPSED
        Producer.send = Mock()
        Consumer.start = Mock()
        self.jdir = tempfile.mkdtemp()
        async.time = Mock(side_effect=now)
        ELAPSED = 0
        
    def tearDown(self):
        shutil.rmtree(self.jdir)

    def testBasic(self):
        global ELAPSED
        
        # setup
        timeout = (5,30)
        watchdog = WatchDog()
        watchdog.journal(self.jdir)
        # tracking
        watchdog.track(SN, REPLYTO, ANY, timeout)
        path = os.path.join(self.jdir, '%s.jnl' % SN)
        self.assertTrue(os.path.exists(path))
        envelope = json.load(open(path))
        self.assertEquals(envelope['sn'], SN)
        self.assertEquals(envelope['idx'], 0)
        self.assertEquals(envelope['ts'][0], NOW+timeout[0])
        self.assertEquals(envelope['ts'][1], NOW+timeout[1])
        self.assertEquals(envelope['ts'][envelope['idx']], NOW+timeout[0])
        self.assertEquals(envelope['replyto'], REPLYTO)
        self.assertEquals(envelope['any'], ANY)
        # started
        watchdog.started(SN)
        envelope = json.load(open(path))
        self.assertEquals(envelope['sn'], SN)
        self.assertEquals(envelope['idx'], 1)
        self.assertEquals(envelope['ts'][0], NOW+timeout[0])
        self.assertEquals(envelope['ts'][1], NOW+timeout[1])
        self.assertEquals(envelope['ts'][envelope['idx']], NOW+timeout[1])
        self.assertEquals(envelope['replyto'], REPLYTO)
        self.assertEquals(envelope['any'], ANY)
        # progress
        watchdog.progress(SN)
        envelope = json.load(open(path))
        self.assertEquals(envelope['sn'], SN)
        self.assertEquals(envelope['idx'], 1)
        self.assertEquals(envelope['ts'][0], NOW+timeout[0])
        self.assertEquals(envelope['ts'][1], NOW+timeout[1])
        self.assertEquals(envelope['ts'][envelope['idx']], NOW+timeout[1])
        self.assertEquals(envelope['replyto'], REPLYTO)
        self.assertEquals(envelope['any'], ANY)
        # progress (with 5 of timeout)
        ELAPSED = 28
        watchdog.progress(SN)
        envelope = json.load(open(path))
        self.assertEquals(envelope['sn'], SN)
        self.assertEquals(envelope['idx'], 1)
        self.assertEquals(envelope['ts'][0], NOW+timeout[0])
        self.assertEquals(envelope['ts'][1], now()+5)
        self.assertEquals(envelope['ts'][envelope['idx']], now()+5)
        # completed
        watchdog.completed(SN)
        path = os.path.join(self.jdir, '%s.jnl' % SN)
        self.assertFalse(os.path.exists(path))


class TestReplyConsumer(TestCase):
    
    def setUp(self):
        Consumer.start = Mock()

    def testBasic(self):
        listener = Mock()
        watchdog = Mock()
        routing = (0,1)
        reply = ReplyConsumer(REPLYTO)
        reply.start(listener, watchdog)
        watchdog.track(SN)
        # started
        reply.dispatch(
            Envelope(sn=SN,
                     routing=routing,
                     any=ANY, 
                     status='started'))
        self.assertTrue(watchdog.started.called_with_args([SN,]))
        self.assertTrue(listener.called)
        arg = listener.call_args[0][0]
        self.assertEquals(arg.sn, SN)
        self.assertEquals(arg.origin, routing[0])
        self.assertEquals(arg.any, ANY)
        # progress
        reply.dispatch(
            Envelope(sn=SN,
                     routing=routing,
                     any=ANY, 
                     status='progress'))
        self.assertTrue(watchdog.progress.called_with_args([SN,]))
        self.assertTrue(listener.called)
        arg = listener.call_args[0][0]
        self.assertEquals(arg.sn, SN)
        self.assertEquals(arg.origin, routing[0])
        self.assertEquals(arg.any, ANY)
        # succeeded
        retval = 123
        reply.dispatch(
            Envelope(sn=SN,
                     routing=routing,
                     any=ANY, 
                     result=Envelope(retval=retval)))
        self.assertTrue(watchdog.completed.called_with_args([SN,]))
        self.assertTrue(listener.called)
        arg = listener.call_args[0][0]
        self.assertEquals(arg.sn, SN)
        self.assertEquals(arg.origin, routing[0])
        self.assertEquals(arg.any, ANY)
        self.assertEquals(arg.retval, retval)
        # failed
        reply.blacklist = set() # reset the blacklist
        exval = 123
        reply.dispatch(
            Envelope(sn=SN,
                     routing=routing,
                     any=ANY, 
                     result=Envelope(exval=exval)))
        self.assertTrue(watchdog.completed.called_with_args([SN,]))
        self.assertTrue(listener.called)
        arg = listener.call_args[0][0]
        self.assertEquals(arg.sn, SN)
        self.assertEquals(arg.origin, routing[0])
        self.assertEquals(arg.any, ANY)
        self.assertEquals(arg.exval.message, exval)
