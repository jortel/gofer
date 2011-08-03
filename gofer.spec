%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?ruby_sitelib: %define ruby_sitelib %(ruby -rrbconfig  -e 'puts Config::CONFIG["sitelibdir"]')}

Name: gofer
Version: 0.43
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
Obsoletes: %{name}-lib
BuildRequires: python
Requires: python-simplejson
Requires: python-qpid >= 0.7
%if 0%{?el5}
Requires: python-uuid
Requires: python-ssl
%endif

%description -n python-%{name}
Contains gofer python lib modules.

%package -n ruby-%{name}
Summary: Gofer ruby lib modules.
Group: Development/Languages
BuildRequires: ruby
Requires: ruby-qpid
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
mkdir -p %{buildroot}/var/lib/%{name}/journal
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
%attr(777, root, root) /var/lib/%{name}/journal

%files -n ruby-%{name}
%defattr(-,root,root,-)
%doc
%{ruby_sitelib}/%{name}
%{ruby_sitelib}/%{name}.rb*
%{ruby_sitelib}/%{name}/*.rb*
%{ruby_sitelib}/%{name}/messaging/
%attr(777, root, root) /var/lib/%{name}/journal

%changelog
* Fri Jul 22 2011 Jeff Ortel <jortel@redhat.com> 0.43-1
- Propigate json exception of return and raised exception values back to
  caller. (jortel@redhat.com)
- Fix topic queue leak that causes: Enqueue capacity threshold exceeded on
  queue. (jortel@redhat.com)
- Add atexit hook to close endpoints. (jortel@redhat.com)
- Fix epydocs. (jortel@redhat.com)

* Wed Jun 22 2011 Jeff Ortel <jortel@redhat.com> 0.42-1
- Simplified thread pool. (jortel@redhat.com)

* Thu Jun 16 2011 Jeff Ortel <jortel@redhat.com> 0.41-1
- python-qpid 0.10 API compat. Specifically on EL6, the Transport.__init__()
  constructor/factory gets called with (con, host, port) instead of (host,
  port) in < 0.10. The 0.10 in F14 still called with (host, port).
  (jortel@redhat.com)

* Thu Jun 16 2011 Jeff Ortel <jortel@redhat.com> 0.40-1
- License as: LGPLv2. (jortel@redhat.com)

* Tue Jun 14 2011 Jeff Ortel <jortel@redhat.com> 0.39-1
- Increase logging in policy. (jortel@redhat.com)
- Add session pool & fix receiver leak in policy. (jortel@redhat.com)
- Testing: enhanced thread pool testing. (jortel@redhat.com)

* Fri May 27 2011 Jeff Ortel <jortel@redhat.com> 0.38-1
- Skip comments when processing config macros. (jortel@redhat.com)
- Queue exceptions caught in the threadpool. (jortel@redhat.com)

* Fri May 13 2011 Jeff Ortel <jortel@redhat.com> 0.37-1
- Fix broker singleton lookup. (jortel@redhat.com)
- Mock call object enhancements. (jortel@redhat.com)

* Mon May 09 2011 Jeff Ortel <jortel@redhat.com> 0.36-1
- Stop receiver thread before closing session. (jortel@redhat.com)
* Tue May 03 2011 Jeff Ortel <jortel@redhat.com> 0.35-1
- Additional concurrency protection; move qpid receiver to ReceiverThread.
  (jortel@redhat.com)
- python 2.4 compat: Queue. (jortel@redhat.com)

* Mon May 02 2011 Jeff Ortel <jortel@redhat.com> 0.34-1
- More robust (receiver) management. (jortel@redhat.com)
- Support getting a list of all mock agent (proxies). (jortel@redhat.com)
- proxy.Agent deprecated. (jortel@redhat.com)
- close() called by __del__() can have AttributeError when consumer never
  started. (jortel@redhat.com)
- Provide means to detect number of proxies. (jortel@redhat.com)
- Singleton enhancements. (jortel@redhat.com)
- Move url translated into producer to proxy.Agent. (jortel@redhat.com)
- add mock.reset(). (jortel@redhat.com)
- Revised and simplified mocks. (jortel@redhat.com)

* Wed Apr 20 2011 Jeff Ortel <jortel@redhat.com> 0.33-1
- Mock history enhancements. (jortel@redhat.com)
- support 'threads' in agent.conf. (jortel@redhat.com)

* Wed Apr 13 2011 Jeff Ortel <jortel@redhat.com> 0.32-1
- Add messaging.theads (cfg) property. (jortel@redhat.com)
- Add support for concurrent RMI dispatching. (jortel@redhat.com)

* Mon Apr 11 2011 Jeff Ortel <jortel@redhat.com> 0.31-1
- Default timeout in specific policies. (jortel@redhat.com)
- Manage invocation policy in stub instead of agent proxy. This provides for
  timeout, async and other flags to be passed in stub constructor.
  (jortel@redhat.com)

* Mon Apr 11 2011 Jeff Ortel <jortel@redhat.com> 0.30-1
- Fix @import of whole sections on machines w/ old versions of iniparse.
  (jortel@redhat.com)

* Wed Apr 06 2011 Jeff Ortel <jortel@redhat.com> 0.29-1
- Refactor mocks; fix NotPermitted. (jortel@redhat.com)
- Mock enhancements. (jortel@redhat.com)
- Fix lockfile. (jortel@redhat.com)
- Stop logging shared secret at INFO. (jortel@redhat.com)

* Wed Mar 30 2011 Jeff Ortel <jortel@redhat.com> 0.28-1
- plugin descriptor & qpid error handling. (jortel@redhat.com)

* Mon Mar 28 2011 Jeff Ortel <jortel@redhat.com> 0.27-1
- Change to yappi profiler. (jortel@redhat.com)
- factor Reader.__fetch() and catch/log fetch exceptions. (jortel@redhat.com)
- Add missing import sleep(). (jortel@redhat.com)

* Thu Mar 24 2011 Jeff Ortel <jortel@redhat.com> 0.26-1
- close sender, huge performance gain. (jortel@redhat.com)
- Add stub Factory. (jortel@redhat.com)

* Tue Mar 22 2011 Jeff Ortel <jortel@redhat.com> 0.25-1
- Use {el5} macro. (jortel@redhat.com)
- Reduce log clutter. (jortel@redhat.com)

* Fri Mar 18 2011 Jeff Ortel <jortel@redhat.com> 0.24-1
- Update secret in options epydoc; fix options override in stub().
  (jortel@redhat.com)
- Add code profiling option. (jortel@redhat.com)
- Add mutex to Broker. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.23-1
- Change receiver READY message to debug. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.22-1
- Change message send/recv to DEBUG. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.21-1
- URL not defined in builtin & main configurations. (jortel@redhat.com)
- Test action every 36 hours. (jortel@redhat.com)
- Start plugin monitor only when URL defined. (jortel@redhat.com)
- Make references to properties on undefined sections safe. (jortel@redhat.com)

* Wed Feb 16 2011 Jeff Ortel <jortel@redhat.com> 0.20-1
- shared in remote decorator may be callable. (jortel@redhat.com)
- Update @remote to support (shared,secret). shared = (0|1): indicates method
  may be shared with other plugins   and called via other uuid's. secret =
  (None, str): A shared secret that must be presented by   the caller and
  included in the RMI request for authentication. The defaults (shared=1,
  secret=None). (jortel@redhat.com)

* Thu Feb 10 2011 Jeff Ortel <jortel@redhat.com> 0.19-1
- ruby: ruby & c++ API expect ttl as miliseconds. (jortel@redhat.com)
- ruby: make non-durable queues auto_delete; make all queues exclusive.
  (jortel@redhat.com)

* Wed Feb 09 2011 Jeff Ortel <jortel@redhat.com> 0.18-1
- Make sure plugins directory exists. (jortel@redhat.com)
- Make file paths portable; fix usage. (jortel@redhat.com)

* Wed Feb 02 2011 Jeff Ortel <jortel@redhat.com> 0.17-1
- Add Obsoletes: gofer-lib. (jortel@redhat.com)
- ruby: Move url/producer options handling to Container. (jortel@redhat.com)
- ruby: replace (puts) with logging. (jortel@redhat.com)

* Tue Feb 01 2011 Jeff Ortel <jortel@redhat.com> 0.16-1
- Fix build requires. (jortel@redhat.com)

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
