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


import os
import re
import socket
from gofer import NAME, Singleton
from iniparse import INIConfig
from iniparse.config import Undefined
from gofer.agent.logutil import getLogger

log = getLogger(__name__)


# makes x.y.z safe when section (y) not defined
def _undefined(self, name):
    return self

Undefined.__getattr__ = _undefined


def ndef(x):
    """
    Section/property not defined.
    @param x: A section/property
    @type x: A section or property object.
    @return: True if not defined.
    """
    return isinstance(x, Undefined)

def nvl(x, d=None):
    """
    Not define value.
    @param x: An object to check.
    @type x: A section/property
    @return: d if not defined, else x.
    """
    if ndef(x):
        return d
    else:
        return x
    
    
class Base(INIConfig):
    """
    Base configuration.
    Uses L{Reader} which provides import.
    """

    def __init__(self, path):
        """
        @param path: The path to an INI file.
        @type path: str
        """
        fp = Reader(path)
        try:
            INIConfig.__init__(self, fp)
        finally:
            fp.close()


class Config(Base):
    """
    The gofer agent configuration.
    @cvar ROOT: The root configuration directory.
    @type ROOT: str
    @cvar PATH: The absolute path to the config directory.
    @type PATH: str
    @cvar USER: The path to an alternate configuration file
        within the user's home.
    @type USER: str
    @cvar ALT: The environment variable with a path to an alternate
        configuration file.
    @type ALT: str
    """
    __metaclass__ = Singleton

    ROOT = '/etc/%s' % NAME
    FILE = 'agent.conf'
    PATH = os.path.join(ROOT, FILE)
    USER = os.path.join('~/.%s' % NAME, FILE)
    CNFD = os.path.join(ROOT, 'conf.d')
    ALT = '%s_OVERRIDE' % NAME.upper()

    def __init__(self):
        """
        Open the configuration.
        Merge (in) alternate configuration file when specified
        by environment variable.
        """
        try:
            Base.__init__(self, self.PATH)
            self.__addconfd()
            altpath = self.__altpath()
            if altpath:
                alt = Base(altpath)
                self.__mergeIn(alt)
                log.info('merged[in]:%s\n%s', altpath, self)
        except:
            log.error(self.PATH, exc_info=1)
            raise
    
    def __update(self, other):
        """
        Update with the specified I{other} configuration.
        @param other: The conf to update with.
        @type other: Base
        @return: self
        @rtype: L{Config}
        """
        for section in other:
            for key in other[section]:
                self[section][key] = other[section][key]
        return self
    
    def __mergeIn(self, other):
        """
        Merge (in) the specified I{other} configuration.
        @param other: The conf to merge in.
        @type other: Base
        @return: self
        @rtype: L{Config}
        """
        for section in other:
            if section not in self:
                continue
            for key in other[section]:
                self[section][key] = other[section][key]
        return self

    def __mergeOut(self, other):
        """
        Merge (out) to the specified I{other} configuration.
        @param other: The conf to merge out.
        @type other: Base
        @return: self
        @rtype: L{Config}
        """
        for section in other:
            if section not in self:
                continue
            for key in other[section]:
                other[section][key] = self[section][key]
        return self

    def write(self):
        """
        Write the configuration.
        """
        altpath = self.__altpath()
        if altpath:
            alt = self.__read(altpath)
            self.__mergeOut(alt)
            log.info('merge[out]:%s\n%s', altpath, alt)
            path = altpath
            s = str(alt)
        else:
            path = self.PATH
            s = str(self)
        fp = open(path, 'w')
        try:
            fp.write(s)
        finally:
            fp.close()

    def __altpath(self):
        """
        Get the I{alternate} configuration path.
        Resolution order: ALT, USER
        @return: The path to the alternate configuration file.
        @rtype: str
        """
        path =  os.environ.get(self.ALT)
        if path:
            return path
        path = os.path.expanduser(self.USER)
        if os.path.exists(path):
            return path
        else:
            None

    def __addconfd(self):
        """
        Read and merge the conf.d files.
        """
        for fn in os.listdir(self.CNFD):
            path = os.path.join(self.CNFD, fn)
            cfg = Base(path)
            self.__update(cfg)
            log.info('updated with: %s\n%s', path, self)


class Properties:
    """
    Import property specification.
    @ivar pattern: The regex for property specification.
    @type pattern: I{regex.pattern}
    @ivar vdict: The variable dictionary.
    @type vdict: dict
    @ivar plain: The list of I{plan} properties to import.
    @type plain: [str,..]
    """

    pattern = re.compile('([^(]+)(\()([^)]+)(\))')
    
    def __init__(self, properties=()):
        """
        @param properties: A list of property specifications.
        @type properties: [str,..]
        """
        self.vdict = {}
        self.plain = []
        for p in properties:
            if not p:
                continue
            m = self.pattern.match(p)
            if m:
                key = m.group(1).strip()
                value = m.group(3).strip()
                self.vdict[key] = value
            else:
                self.plain.append(p) 
                
    def isplain(self, property):
        """
        Get whether a property is I{plain} and is to be imported.
        @param property: A property name.
        @type property: str
        @return: True when property is to be imported.
        @rtype: bool
        """
        return ( property in self.plain )
    
    def var(self, property):
        """
        Get the property's declared variable name.
        @param property: A property name.
        @type property: str
        @return: The variable name declared for the property
            or None when not declared.
        @rtype: str
        """
        return self.vdict.get(property)
    
    def empty(self):
        """
        Get whether the object is empty.
        @return: True no properties defined.
        @rtype: bool
        """
        return ( len(self) == 0 )
    
    def __iter__(self):
        keys = self.vdict.keys()
        keys += self.plain
        return iter(keys)
    
    def __len__(self):
        return ( len(self.vdict)+len(self.plain) )
    
    
class Import:
    """
    Represents an import directive.
    @@import:<path>:<section>:<property>,
    where <property> is: <name>|<name>(<variable>).
    When the <variable> form is used, a variable is assigned the value 
    to be used as $(var) in the conf rather than imported.
    @cvar allproperties: An (empty) object representing all properties
        are to be imported.
    @type allproperties: L{Properties}
    @ivar path: The path to the imported ini file.
    @type path: str
    @ivar section: The name of the section to be imported.
    @type section: str
    @ivar properties: The property specification.
    @type properties: L{Properties}
    """
    
    allproperties = Properties()

    def __init__(self, imp):
        """
        @param imp: An import directive.
        @type imp: str
        """
        part = imp.split(':')
        self.path = part[1]
        self.section = None
        self.properties = self.allproperties
        if len(part) > 2:
            self.section = part[2].strip()
        if len(part) > 3:
            plist = [s.strip() for s in part[3].split(',')]
            self.properties = Properties(plist)
    
    def __call__(self):
        """
        Execute the import directive.
        @return: The (imported) lines & declared (vdict) variables.
        @rtype: tuple(<imported>,<vdict>)
        """
        vdict = {}
        input = Base(self.path)
        if not self.section:
            return (input, vdict)
        imported = INIConfig()
        S = input[self.section]
        if ndef(S):
            raise Exception, '[%s] not found in %s' % (self.section, self.path)
        for k in S:
            v = input[self.section][k]
            if self.properties.empty() or self.properties.isplain(k):
                ts = getattr(imported, self.section)
                setattr(ts, k, v)
            else:
                var = self.properties.var(k)
                if var:
                    var = '$(%s)' % var.strip()
                    vdict[var] = v
        return (imported, vdict)
    
    
def _cnfvalue(macro):
    """
    configuration macro resolver
    @return: The resolved configuration value
    @rtype: str
    """
    n = macro[2:-1]
    cfg = Config()
    s,p = n.split('.',1)
    return nvl(cfg[s][p])
    

class Reader:
    """
    File reader.
    post-process directives.
    @ivar idx: The line index.
    @type idx: int
    @ivar vdict: The variable dictionary.
    @type vdict: dict
    @ivar path: The path to a file to read.
    @type path: str
    """
    
    MACROS = {
        '%{hostname}':socket.gethostname(),
        '%{messaging.url}':_cnfvalue,
        '%{messaging.cacert}':_cnfvalue,
        '%{messaging.clientcert}':_cnfvalue,
        }
    
    def __init__(self, path):
        self.idx = 0
        self.vdict = {}
        self.path = path
        log.info('reading: %s', path)
        f = open(path)
        try:
            bfr = f.read()
            self.lines = self.__post(bfr.split('\n'))
        finally:
            f.close()

    def readline(self):
        """
        read the next line.
        @return: The line of None on EOF.
        @rtype: str 
        """
        if self.idx < len(self.lines):
            ln = self.lines[self.idx]
            self.idx += 1
            return ln+'\n'
        
    def close(self):
        pass

    def __post(self, input):
        """
        Post-process file content for directives.
        @param input: The file content (lines).
        @type input: list
        @return: The post processed content.
        @rtype: list
        """
        output = []
        for ln in input:
            if ln.startswith('@import'):
                for ln in self.__import(ln):
                    output.append(ln)
            else:
                ln = self.__repl(ln)
                output.append(ln)
        return output

    def __import(self, ln):
        """
        Procecss an i{import} directive and return the result.
        @param ln: A line containing the directive.
        @type ln: str
        @return: The import result (lines).
        @rtype: [str,..]
        """
        log.info('processing: %s', ln)
        imp = Import(ln)
        imported, vdict = imp()
        self.vdict.update(vdict)
        return str(imported).split('\n')
    
    def __repl(self, ln):
        """
        Replace variables contained in the line.
        @param ln: A file line.
        @type ln: str
        @return: The line w/ vars replaced.
        @rtype: str
        """
        if ln.startswith('#'):
            return ln
        for k,v in self.MACROS.items()+self.vdict.items():
            if k in ln:
                if callable(v):
                    v = v(k)
                log.info('line "%s" s/%s/%s/', ln, k, v)
                ln = ln.replace(k, v)
        return ln
    
    def __str__(self):
        return self.path


if __name__ == '__main__':
    cfg = Config()
    print cfg