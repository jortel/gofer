# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )
#

PKG = gofer
SPEC = $(PKG).spec
SETUP = setup.py
DOCTAR = gofer-docs.tar.gz
FEDORAPEOPLE = jortel@fedorapeople.org
TITODIR = /tmp/tito

release : rpm rdocs
	scp `find $(TITODIR) -name \*.rpm` fedorahosted.org:gofer

rpm	:
	rm -rf $(TITODIR)
	tito build --rpm

rdocs : docs
	scp /tmp/$(DOCTAR) $(FEDORAPEOPLE):
	ssh $(FEDORAPEOPLE) 'cd public_html/gofer; rm -rf doc; tar xmzvf ~/$(DOCTAR)'

docs :
	rm -rf doc
	rm -f /tmp/$(DOCTAR)
	epydoc -vo doc `find src/gofer -name "*.py"`
	tar czvf /tmp/$(DOCTAR) doc

pdf :
	epydoc -vo doc --pdf `find src/gofer -name \*.py`
	mv doc/api.pdf doc/gofer.pdf

clean :
	rm -rf doc
	rm -rf src/dist
	rm -rf src/build
	rm -rf src/$(PKG).egg-info
	rm -rf /usr/src/redhat/BUILD/$(PKG)*
	rm -rf /usr/src/redhat/RPMS/noarch/$(PKG)*
	rm -rf /usr/src/redhat/SOURCES/$(PKG)*
	rm -rf /usr/src/redhat/SRPMS/$(PKG)*
	find . -name "*.pyc" -exec rm -f {} \;
	find . -name "*~" -exec rm -f {} \;

.PHONY : clean docs pdf
