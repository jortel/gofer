# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name: gopher
Version: 0.1
Release: 2%{?dist}
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
mkdir -p %{buildroot}/etc/init.d
mkdir -p %{buildroot}/var/log/%{name}
mkdir -p %{buildroot}/var/lib/%{name}/plugins

cp bin/%{name}d %{buildroot}/usr/bin
cp etc/init.d/%{name}d %{buildroot}/etc/init.d
cp etc/%{name}/* %{buildroot}/etc/%{name}
cp src/plugins/*.py %{buildroot}/var/lib/%{name}/plugins

rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc
%{python_sitelib}/%{name}/agent/
%{_bindir}/%{name}d
%attr(755,root,root) %{_sysconfdir}/init.d/%{name}d
%config(noreplace) %{_sysconfdir}/%{name}/agent.conf
/var/lib/%{name}/plugins/

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
* Thu Sep 30 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- 0.1
