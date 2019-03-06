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

dir="$(mktemp -d -t)"
nosetests="nosetests-3"
virtualenv="virtualenv-3"
pip="pip3"

clean()
{
  find ../ -name .coverage -exec rm -rf {} \;
}

run()
{
  echo $dir
  ${virtualenv} $dir
  source $dir/bin/activate
  ${pip} install nose
  ${pip} install nose-cov
  ${pip} install mock
  ${pip} install iniparse
  ${pip} install -e ../src/
  ${nosetests} --with-coverage --cover-package=gofer `find unit -type d`
}

main()
{
  clean
  run
  clean
}

main
