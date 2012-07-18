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
from gofer.messaging import getuuid, Queue
from gofer.messaging.consumer import Consumer, Reader
from gofer.messaging.producer import Producer, BinaryProducer
from logging import getLogger

log = getLogger(__name__)

#
# Utils
#

def toq(uuid):
    return Queue(uuid, durable=False)


#
# Tunnel Endpoints
# TCP->Gateway->Bridge->TCP
#


class Bridge(Consumer):
    
    HOST = socket.gethostname()
    
    def __init__(self, url, uuid, port, host=HOST):
        Consumer.__init__(self, toq(uuid), url=url)
        self.uuid = uuid
        self.port = port
        self.host = host
        
        
    def dispatch(self, env):
        peer = env.peer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        uuid = toq(getuuid())
        p = Producer(url=self.url)
        p.send(env.peer, peer=str(uuid))
        reader = Reader(uuid, url=self.url)
        tr = TunnelReader(reader, sock)
        tr.start()
        tw = TunnelWriter(self.url, env.peer, sock)
        tw.start()
   

class Gateway(Thread):
    
    def __init__(self, url, peer, port):
        Thread.__init__(self)
        self.url = url
        self.peer = peer
        self.port = int(port)
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
        uuid = toq(getuuid())
        p = Producer(url=self.url)
        p.send(toq(self.peer), peer=str(uuid))
        r = Reader(uuid, url=self.url)
        env = r.next()
        tr = TunnelReader(r, sock)
        tr.start()
        tw = TunnelWriter(self.url, env.peer, sock)
        tw.start()
        

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
        producer = BinaryProducer(url=self.url)
        while True:
            content = self.__read()
            if content:
                producer.send(self.queue, content)
            else:
                producer.send(self.queue, '')
                self.close()
                break
            
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