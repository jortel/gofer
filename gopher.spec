# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name: gopher
Version: 0.7
Release: 1%{?dist}
Summary: A lightweight, extensible python agent.
Group:   Development/Languages
License: GPLv2
URL: https://fedorahosted.org/gopher/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: rpm-python
Requires: %{name}-common = %{version}

%description
Gopher provides a lightweight, extensible python agent.

%package common
Summary: Gopher common modules.
Group: Development/Languages
BuildRequires: rpm-python
Requires: python-simplejson
Requires: python-qpid >= 0.7

%description common
Contains common gopher modules.

%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/etc/%{name}
mkdir -p %{buildroot}/etc/%{name}/plugins
mkdir -p %{buildroot}/etc/%{name}/conf.d
mkdir -p %{buildroot}/etc/init.d
mkdir -p %{buildroot}/var/log/%{name}
mkdir -p %{buildroot}/usr/lib/%{name}/plugins

cp bin/%{name}d %{buildroot}/usr/bin
cp etc/init.d/%{name}d %{buildroot}/etc/init.d
cp etc/%{name}/*.conf %{buildroot}/etc/%{name}
cp etc/%{name}/plugins/*.conf %{buildroot}/etc/%{name}/plugins
cp src/plugins/*.py %{buildroot}/usr/lib/%{name}/plugins

rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc
%dir %{_sysconfdir}/%{name}/conf.d/
%{python_sitelib}/%{name}/agent/
%{_bindir}/%{name}d
%attr(755,root,root) %{_sysconfdir}/init.d/%{name}d
%config(noreplace) %{_sysconfdir}/%{name}/agent.conf
%config %{_sysconfdir}/%{name}/plugins/*.conf
/usr/lib/%{name}/plugins/

%post
chkconfig --add %{name}d

%preun
if [ $1 = 0 ] ; then
   /sbin/service %{name}d stop >/dev/null 2>&1
   /sbin/chkconfig --del %{name}d
fi

%files common
%defattr(-,root,root,-)
%doc
%{python_sitelib}/%{name}/*.py*
%{python_sitelib}/%{name}/messaging/

%changelog
* Tue Nov 02 2010 Jeff Ortel <jortel@redhat.com> 0.7-1
- Mangle plugin module name when found in the path to prevent name collisions.
  (jortel@redhat.com)
- Update plugin importer to be more precise. (jortel@redhat.com)
- Fix intermittent problem whereby gopherd allows multiple instances.
  (jortel@redhat.com)
- Add builtin admin.help(). (jortel@redhat.com)
- Rename demo (plugin) to builtin. (jortel@redhat.com)
- Replace /var/lib with: /usr/lib for plugins. (jortel@redhat.com)

* Mon Nov 01 2010 Jeff Ortel <jortel@redhat.com> 0.6-1
- Move gopher plugins to proper location /usr/lib. (jortel@redhat.com)
- Change 'id' parameter to be uuid. (jortel@redhat.com)
- Add AgentAdmin back to test agent. (jortel@redhat.com)
- add getcert() to Identity. (jortel@redhat.com)
- Fix demo Identity plugin. (jortel@redhat.com)
- fix epydocs. (jortel@redhat.com)

* Tue Oct 26 2010 Jeff Ortel <jortel@redhat.com> 0.5-1
- Make identity plugin a class. (jortel@redhat.com)

* Tue Oct 26 2010 Jeff Ortel <jortel@redhat.com> 0.4-1
- Add conf.d/ processing. (jortel@redhat.com)

* Tue Oct 26 2010 Jeff Ortel <jortel@redhat.com> 0.3-1
- Add conf.d/ processing. (jortel@redhat.com)
- Add decorator module for convenient import. (jortel@redhat.com)
- Comment out the demo identity plugin. (jortel@redhat.com)
- Add identity plugin. (jortel@redhat.com)
- Update epydocs. (jortel@redhat.com)
- Add support for plugin to get configuration. (jortel@redhat.com)
- Add plugin descriptors. (jortel@redhat.com)
- Add makefile and fix epydocs. (jortel@redhat.com)

* Thu Oct 14 2010 Jeff Ortel <jortel@redhat.com> 0.2-1
- Fix tito/rpm build errors.

* Thu Sep 30 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- 0.1
