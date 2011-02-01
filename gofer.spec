%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?ruby_sitelib: %define ruby_sitelib %(ruby -rrbconfig  -e 'puts Config::CONFIG["sitelibdir"]')}

Name: gofer
Version: 0.15
Release: 1%{?dist}
Summary: A lightweight, extensible python agent.
Group:   Development/Languages
License: GPLv2
URL: https://fedorahosted.org/gofer/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: rpm-python
Requires: python-%{name} = %{version}

%description
Gofer provides a lightweight, extensible python agent.

%package -n python-%{name}
Summary: Gofer python lib modules.
Group: Development/Languages
BuildRequires: rpm-python
Requires: python-simplejson
Requires: python-qpid >= 0.7
%if !0%{?fedora}
Requires: python-uuid
Requires: python-ssl
%endif

%description -n python-%{name}
Contains gofer python lib modules.

%package -n ruby-%{name}
Summary: Gofer ruby lib modules.
Group: Development/Languages
BuildRequires: rubygems
Requires: rubygems
Requires: rubygem(json)

%description -n ruby-%{name}
Contains gofer ruby lib modules.

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
pushd ruby
mkdir -p %{buildroot}/%{ruby_sitelib}/%{name}/messaging
cp %{name}.rb %{buildroot}/%{ruby_sitelib}
pushd %{name}
cp *.rb %{buildroot}/%{ruby_sitelib}/%{name}
pushd messaging
cp *.rb %{buildroot}/%{ruby_sitelib}/%{name}/messaging
popd
popd
popd
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

%files -n python-%{name}
%defattr(-,root,root,-)
%doc
%{python_sitelib}/%{name}/*.py*
%{python_sitelib}/%{name}/messaging/

%files -n ruby-%{name}
%defattr(-,root,root,-)
%doc
%{ruby_sitelib}/%{name}
%{ruby_sitelib}/%{name}.rb*
%{ruby_sitelib}/%{name}/*.rb*
%{ruby_sitelib}/%{name}/messaging/

%changelog
* Mon Jan 31 2011 Jeff Ortel <jortel@redhat.com> 0.15-1
- ruby: symbolize JSON key names; Fix proxy constructor. (jortel@redhat.com)
- Add timeout support using Timeout since ruby-qpid does not support
  Queue.get() w/ timeout arg. (jortel@redhat.com)
- Replace stub() method w/ StubFactory(). (jortel@redhat.com)
- Add keyword (options) to Stub pseudo constructor. Supports Eg: dog =
  agent.Dog(window=mywin, any=100). Update async test to use ctag = XYZ.
  (jortel@redhat.com)
- Fix & simplify inherited messaging properties. Name ReplyConsumer properly.
  (jortel@redhat.com)
- Add ruby packaging. (jortel@redhat.com)
- Make messaging completely centric. * Add [messaging] section to plugin
  descriptor. * Remove messaging.enabled property. * Refactor plugin monitor
  thread to be 1 thread/plugin. * Clean up decorated /Remote/ functions when
  plugin fails to load. (jortel@redhat.com)
- Add ruby (client) API bindings. (jortel@redhat.com)

* Thu Jan 20 2011 Jeff Ortel <jortel@redhat.com> 0.14-1
- Fix conditional for pkgs required on RHEL. (jortel@redhat.com)

* Wed Jan 12 2011 Jeff Ortel <jortel@redhat.com> 0.13-1
- Make Broker a smart singleton. (jortel@redhat.com)
- py 2.4 compat: replace @singleton class decorator with __metaclass__
  Singleton. (jortel@redhat.com)
- Log dispatch exceptions. (jortel@redhat.com)

* Wed Jan 05 2011 Jeff Ortel <jortel@redhat.com> 0.12-1
- Adjust sleep times & correct log messages. (jortel@redhat.com)
- Make logging (level) configurable. (jortel@redhat.com)
- Remove @identity decorator. (jortel@redhat.com)

* Tue Jan 04 2011 Jeff Ortel <jortel@redhat.com> 0.11-1
- Quiet logged Endpoint.close() not checking for already closed.
  (jortel@redhat.com)
- Replace builtin variables with macros (format=%{macro}). (jortel@redhat.com)
- make Config a singleton; Make PluginDescriptor a 'Base' config.
  (jortel@redhat.com)
- Add support for @import directive. (jortel@redhat.com)
- The server test needs to use the correct uuid. (jortel@redhat.com)

* Wed Dec 15 2010 Jeff Ortel <jortel@redhat.com> 0.10-1
- session.stop() not supported in python-qpid 0.7. (jortel@redhat.com)
- Remove unused catch. (jortel@redhat.com)
- Make worker threads daemons. (jortel@redhat.com)

* Mon Dec 13 2010 Jeff Ortel <jortel@redhat.com> 0.9-1
- Set AMQP message TTL=timeout for synchronous RMI. (jortel@redhat.com)

* Thu Dec 09 2010 Jeff Ortel <jortel@redhat.com> 0.8-1
- Fix RHEL requires. (jortel@redhat.com)
- Enable module (level) access to plugin descriptor (conf). (jortel@redhat.com)

* Wed Dec 08 2010 Jeff Ortel <jortel@redhat.com> 0.7-1
- Support timeout as tuple. (jortel@redhat.com)
- Enhanced exception propagation. (jortel@redhat.com)
- Fix testings. (jortel@redhat.com)

* Fri Dec 03 2010 Jeff Ortel <jortel@redhat.com> 0.6-1
- Reverse presidence of uuid: plugin descriptor now overrides @identity
  function/method. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.5-1
- python 2.4 (& RHEL 5) compatibility. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.4-1
- Modify builtin (generated) uuid to be persistent. (jortel@redhat.com)
- Use hostname for 'builtin' plugin's uuid. Use the hostname unless it is non-
  unique such as 'localhost' or 'localhost.localdomain'. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.3-1
- Set 'builtin' plugin back to uuid=123. (jortel@redhat.com)
- Re-specify exclusive queue subscription; filter plugin descriptors by ext.
  (jortel@redhat.com)
- Add support for each plugin to specify a messaging consumer (uuid).
  (jortel@redhat.com)
- Rename builtin AgentAdmin to just Admin. (jortel@redhat.com)
- Replace class decorators for python 2.4 compat. (jortel@redhat.com)
- Fix cvs tags. (jortel@redhat.com)
- Automatic commit of package [gofer] release [0.2-1]. (jortel@redhat.com)
- Add brew build informaton. (jortel@redhat.com)

* Fri Nov 19 2010 Jeff Ortel <jortel@redhat.com> 0.2-1
- Add brew build informaton. (jortel@redhat.com)
- Fix test. (jortel@redhat.com)

* Mon Nov 08 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- new package built with tito

* Thu Sep 30 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- 0.1
