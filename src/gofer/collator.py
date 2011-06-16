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

"""
Provides decorator collator classes.
"""

import inspect


class Collator:
    """
    Docorated method/function collator.
    """
    
    def collate(self, functions):
        """
        Collate decorated functions/methods.
        Returns (Classes, Unbound) where:
            - Classes is: dict {class:[methods,..]}
            - Unbound is: dict {module: [functions,...]}
        @param functions: A collection of decorated functions.
        @type functions: (list|dict)
        @return: A tuple (classes, unbound)
        @rtype: tuple(2)
        """
        self.classes = {}
        self.bound = set()
        self.functions = functions
        mapped = []
        for fn in functions:
            g = fn.func_globals
            if g in mapped:
                continue
            self.__map(g)
            mapped.append(g)
        return (self.classes, self.__functions())
    
    def __map(self, g):
        for cls in self.__classes(g):
            for method in self.__methods(cls):
                fn = self.__function(method)
                decorated = self.__decorated(fn)
                if not decorated:
                    continue
                self.bound.add(fn)
                methods = self.__find(cls)
                methods.append((method, decorated[1]))
                
    def __find(self, cls):
        methods = self.classes.get(cls)
        if methods is None:
            methods = []
            self.classes[cls] = methods
        return methods
    
    def __classes(self, g):
        classes = []
        for x in g.values():
            if inspect.isclass(x):
                classes.append(x)
        return classes
    
    def __methods(self, cls):
        return [v for n,v in \
                inspect.getmembers(cls, inspect.ismethod)]
        
    def __function(self, method):
        for n,v in inspect.getmembers(method, inspect.isfunction):
            return v
        
    def __functions(self):
        modules = {}
        for fn in self.functions:
            if fn in self.bound:
                continue
            mod = inspect.getmodule(fn)
            functions = modules.get(mod)
            if not functions:
                functions = []
                modules[mod] = functions
            functions.append(self.__decorated(fn))
        return modules
    
    def __decorated(self, fn):
        if fn in self.functions:
            if isinstance(self.functions, dict):
                return (fn, self.functions[fn])
            else:
                return (fn, None)
