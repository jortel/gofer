#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#


import socket

from threading import Thread
from uuid import uuid4

from gofer.messaging.consumer import Consumer
from gofer.messaging.adapter.model import Queue, Reader, Producer, Sender, Address
from logging import getLogger

log = getLogger(__name__)


#
# Tunnel Endpoints
# TCP->Gateway->Bridge->TCP
#


class Bridge(Consumer):
    
    HOST = socket.gethostname()
    
    def __init__(self, url, uuid, port, host=HOST):
        Consumer.__init__(self, Queue(uuid), url)
        self.uuid = uuid
        self.port = port
        self.host = host

    def dispatch(self, env):
        peer = env.peer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        p = Producer(self.url)
        try:
            peer = Address(self.queue.name)
            p.send(env.peer, peer=peer.dict())
        finally:
            p.close()
        r = Reader(self.queue, self.url)
        try:
            tr = TunnelReader(r, sock)
            tr.start()
            tw = TunnelWriter(self.url, env.peer, sock)
            tw.start()
        finally:
            r.close()
   

class Gateway(Thread):
    
    def __init__(self, url, peer, port):
        Thread.__init__(self)
        self.url = url
        self.peer = peer
        self.port = int(port)
        self.url = url
        self.setDaemon(True)
        
    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((socket.gethostname(), self.port))
        sock.listen(5)
        while True:
            (client, address) = sock.accept()
            try:
                self.accepted(client)
            except Exception:
                log.exception(address)
    
    def accepted(self, sock):
        uuid = str(uuid4())
        queue = Queue(uuid)
        p = Producer(self.url)
        try:
            peer = Address(queue.name)
            p.send(self.peer, peer=peer.dict())
        finally:
            p.close()
        r = Reader(queue, self.url)
        try:
            env = r.next()
            tr = TunnelReader(r, sock)
            tr.start()
            tw = TunnelWriter(self.url, env.peer, sock)
            tw.start()
        finally:
            r.close()
        

class TunnelReader(Thread):
    
    def __init__(self, reader, sock):
        Thread.__init__(self)
        self.reader = reader
        self.sock = sock
        self.setDaemon(True)
    
    def run(self):
        try:
            self.__read()
        finally:
            self.reader.close()
    
    def __read(self):
        self.sock.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY, 1)
        while True:
            m = self.reader.read(5)
            if not m:
                continue
            if m.content:
                n = self.__write(m.content)
                if n == 0:
                    # broken
                    break
            else:
                # eof
                self.close()
                break
            
    def __write(self, content):
        try:
            return self.sock.send(content)
        except:
            return 0
            
    def close(self):
        try:
            self.sock.close()
        except:
            pass


class TunnelWriter(Thread):
    
    BUFSIZE = 0x100000
    
    def __init__(self, url, queue, sock):
        Thread.__init__(self)
        self.url = url
        self.sock = sock
        self.queue = queue
        self.setDaemon(True)
    
    def run(self):
        p = Sender(self.url)
        try:
            while True:
                content = self.__read()
                if content:
                    p.send(self.queue, content)
                else:
                    p.send(self.queue, '')
                    self.close()
                    break
        finally:
            p.close()
            
    def __read(self):
        try:
            return self.sock.recv(self.BUFSIZE)
        except:
            pass
            
    def close(self):
        try:
            self.sock.close()
        except:
            pass


#
# Testing
#

UUID = 'GATEWAY'
URL = 'tcp://localhost:5672'

if __name__ == '__main__':
    from logging import basicConfig
    basicConfig()
    b = Bridge(URL, UUID, 443)
    b.start()
    g = Gateway(URL, UUID, 9443)
    g.start()
    g.join()