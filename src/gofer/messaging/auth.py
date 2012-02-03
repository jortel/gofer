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

import hmac
from gofer import *
from threading import RLock

#
# Util
#

def resolved(key):
    if callable(key):
        return key()
    else:
        return key
    

#
# Exceptions
#

class MessageDigest(Exception):
    
    def __str__(self):
        return 'digest: "%s" for: uuid=%s, not matched' % \
            (self.args[0],
             self.args[1])

#
# KeyChains
# 

class KeyChain(object):
    
    signing = property(
        fget=lambda self: self.get(0),
        fset=lambda self,v: self.set(0, v),
        fdel=lambda self: self.unset(0))
    
    validation = property(
        fget=lambda self: self.get(1),
        fset=lambda self,v: self.set(1, v),
        fdel=lambda self: self.unset(1))
    
    def __init__(self, **keychain):
        self.__mutex = RLock()
        self.__keydict = {}
        self.update(keychain)

    @synchronized
    def get(self, id, d=None):
        key = self.__keydict.get(id, d)
        return resolved(key)
    
    @synchronized 
    def set(self, id, key):
        if key:
            self.__keydict[id] = key
        else:
            self.unset(id)
    
    @synchronized
    def unset(self, id):
        self.__keydict.pop(id, None)
    
    @synchronized
    def update(self, d):
        if isinstance(d, KeyChain):
            self.__keydict.update(d.keydict())
        else:
            self.__keydict.update(d)
            
    @synchronized
    def find(self, role, id, d=None):
        key = self.get(id)
        if key:
            return resolved(key)
        key = self.get(role)
        if key:
            return resolved(key)
        return d

    @synchronized    
    def keydict(self):
        return dict(self.__keydict)
    
    @synchronized
    def __setitem__(self, id, key):
        self.__keydict[id] = key
    
    @synchronized
    def __getitem__(self, id):
        key = self.__keydict[id]
        return resolved(key)
    
    @synchronized
    def __repr__(self):
        return repr(self.__keydict)
    
    @synchronized
    def __str__(self):
        return str(self.__keydict)
        
        
class KeyPair(object):

    signing = property(
        fget=lambda self: self.__get(0),
        fset=lambda self,v: self.__set(0, v),
        fdel=lambda self: self.__set(0))
    
    validation = property(
        fget=lambda self: self.__get(1),
        fset=lambda self,v: self.__set(1, v),
        fdel=lambda self: self.__set(1))

    def __init__(self, signing=None, validation=None):
        self.__mutex = RLock()
        self.__keydict = {}
        if signing:
            self.signing = signing
        if validation:
            self.validation = validation
        
    @synchronized
    def find(self, role, id, d=None):
        return self.__get(role, d)
    
    @synchronized
    def __get(self, id, d=None):
        key = self.__keydict.get(id, d)
        return resolved(key)
    
    @synchronized
    def __set(self, id, key=None):
        if key:
            self.__keydict[id] = key
        else:
            self.__keydict.pop(id, None)
    
    @synchronized    
    def keydict(self):
        return dict(self.__keydict)
    
    @synchronized
    def __str__(self):
        return str(self.__keydict)
    
    
class Key(str):

    def find(self, role, id, d=None):
        return self

#
# Authentication
#

class Auth:
    
    def __init__(self, keychain=KeyChain()):
        self.keychain = keychain
        
    def sign(self, envelope):
        envelope.pop('digest', None)
        uuid = envelope.routing[0]
        key = self.keychain.find(0, uuid)
        hash = hmac.new(key)
        hash.update(repr(envelope))
        envelope.digest = hash.hexdigest()
        return envelope
    
    def signed(self, envelope):
        return (envelope.digest is not None)

    def validate(self, envelope):
        __digest = envelope.pop('digest', None)
        if not __digest:
            return
        uuid = envelope.routing[0]
        key = self.keychain.find(1, uuid)
        hash = hmac.new(key)
        hash.update(repr(envelope))
        digest = hash.hexdigest()
        if digest != __digest:
            raise MessageDigest(digest, uuid)
        envelope.digest = __digest

#
# Testing
#

from gofer.messaging import Envelope

def test1():    
    kr = KeyChain(A='0xAA',B='0xBB')
    e = Envelope(routing=('A','B'))
    auth = Auth(kr)
    signed = auth.sign(e)
    print signed
    auth.validate(signed)
    print 'validated'

def keyA():
    return '0xAA'
def keyB():
    return '0xBB'

def test2():
    # sender    
    krA = KeyPair(signing='0xAA',validation=keyB)
    e = Envelope(routing=('A','B'))
    authA = Auth(krA)
    signed = authA.sign(e)
    print signed
    # receiver
    received = signed
    krB = KeyPair(signing='0xBB',validation=keyA)
    print 'krB: %s' % krB
    authB = Auth(krB)
    authB.validate(received)
    print 'validated (1)'
    # receiver-2
    received = signed
    print 'krA: %s' % krA
    krA.signing='0xBB'
    krA.validation='0xAA'
    print 'krA: %s' % krA
    authA.validate(received)
    print 'validated (2)'

def test3():
    # sender    
    master = Key('0xAA')
    e = Envelope(routing=('A','B'))
    authA = Auth(master)
    signed = authA.sign(e)
    print signed
    # receiver
    master = Key('0xAA')
    received = signed
    authB = Auth(master)
    authB.validate(received)
    print 'test3:validated'

if __name__ == '__main__':
    test1()
    test2()
    test3()