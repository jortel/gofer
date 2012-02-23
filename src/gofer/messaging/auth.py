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
# Decorator
#
def resolved(fn):
    def _fn(*a,**k):
        k = fn(*a,**k)
        if callable(k):
            return k()
        else:
            return k
    return _fn


#
# Exceptions
#

class MessageDigest(Exception):
    
    def __str__(self):
        return 'digest: "%s" for: uuid=%s, not matched' % \
            (self.args[0],
             self.args[1])

#
# KeyChain
#

class Role:

    ROLES = {
        0:'signing',
        1:'validation',
        'signing':0,
        'validation':1,}

    def __init__(self, id):
        if isinstance(id, str):
            self.id = self.ROLES[id]
        else:
            self.id = id
        
    def __str__(self):
        return self.ROLES[self.id]
    
    def __int__(self):
        return self.id
    
    
class KeyPair:

    def __init__(self, kp):
        if isinstance(kp, dict):
            self.dict = {}
            for k,v in kp.items():
                r = Role(k)
                self.dict[int(r)] = v
            return
        if isinstance(kp, str):
            self.dict = {0:kp, 1:kp}
            return
        if callable(kp):
            self.dict = {0:kp, 1:kp}
            return
        if isinstance(kp, (tuple,list)):
            self.dict = {0:kp[0], 1:kp[1]}
            return
        raise ValueError(kp)

    def valid(self):
        err = 0
        for k in (0, 1):
            v = self.dict.get(k)
            if isinstance(v, str):
                continue
            if callable(v):
                continue
            err += 1
        return (err == 0)


class KeyChain(object):
    
    DEFAULT = None
    
    def __init__(self, **keychain):
        self.__mutex = RLock()
        self.__keydict = {}
        self.update(keychain)
        
    def add(self, id, *kp, **roles):
        self.set(id, *kp, **roles)
        
    def default(self, *kp, **roles):
        self.set(self.DEFAULT, *kp, **roles)
        
    @synchronized
    def clear(self):
        self.__keydict = {}
    
    @synchronized 
    def set(self, id, *kp, **roles):
        if len(kp) == 0:
            kp = KeyPair(roles)
            if kp.valid():
                self.__keydict[id] = kp.dict
            else:
                raise ValueError()
            return
        if len(kp) == 1:
            kp = KeyPair(kp[0])
            self.__keydict[id] = kp.dict
            return
        if len(kp) == 2:
            kp = KeyPair(kp)
            self.__keydict[id] = kp.dict
            return
        raise ValueError()
    
    @synchronized
    def unset(self, id):
        self.__keydict.pop(id, None)
    
    @synchronized
    def update(self, d):
        if isinstance(d, KeyChain):
            self.__keydict.update(d.dict())
            return
        for k,v in d.items():
            self.set(k,v)

    @synchronized
    def get(self, id, d=None):
        return self.__keydict.get(id, d)
    
    @resolved
    @synchronized
    def find(self, role, id, d=None):
        kp = self.get(id)
        if not kp:
            kp = self.get(self.DEFAULT)
        if kp:
            key = kp.get(role)
        else:
            key = d
        return key

    @synchronized
    def dict(self):
        return dict(self.__keydict)
    
    @synchronized
    def __setitem__(self, id, kp):
        self.set(id, kp)

    @synchronized
    def __getitem__(self, id):
        return self.__keydict[id]
    
    @synchronized
    def __repr__(self):
        return repr(self.__keydict)
    
    @synchronized
    def __str__(self):
        return str(self.__keydict)


#
# Authentication
#

class Auth:
    
    def __init__(self, keychain=KeyChain()):
        self.keychain = keychain
        
    def sign(self, envelope):
        envelope.pop('digest', None)
        uuid = envelope.routing[1]
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
    e = Envelope(routing=('A','B'))
    kr = KeyChain(B=('0xAA', '0xBB'))
    auth = Auth(kr)
    signed = auth.sign(e)
    print signed
    kr = KeyChain(A=('0xBB', '0xAA'))
    auth = Auth(kr)
    auth.validate(signed)
    print 'test1:validated'


def test2():
    # A
    routing=('A','B')
    e = Envelope(routing=routing)
    kr = KeyChain()
    kr.set('B', '0xAA', '0xBB')
    kr.set('C', ('0xXX', '0xYY'))
    kr.set('D', {0:'0xXX', 1:'0xYY'})
    T = ('C', '0xGG', '0xZZ')
    kr.set(*T)
    auth = Auth(kr)
    signed = auth.sign(e)
    print signed
    # B
    kr = KeyChain()
    kr.add('A', signing='0xBB', validation='0xAA')
    auth = Auth(kr)
    auth.validate(signed)
    print 'test2:validated'  

def test3():
    def keyfn():return '0xDEADBEAF'
    routing=('A','B')
    e = Envelope(routing=routing)
    kr = KeyChain()
    kr.default(keyfn)
    auth = Auth(kr)
    signed = auth.sign(e)
    auth.validate(signed)
    print 'test3:validated' 

if __name__ == '__main__':
    test1()
    test2()
    test3()