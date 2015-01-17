%global build_sample_subpackage 0
%global dbus_send /bin/dbus-send

Name: oddjob
Version: 0.30
Release: 5
Source: http://fedorahosted.org/released/oddjob/oddjob-%{version}.tar.gz
Patch0: oddjob-0.30-noclose.patch
Patch1: oddjob-0.30-umasks.patch
Patch2: oddjob-0.30-tests.patch
Patch3: oddjob-init-status.patch
Summary: A D-Bus service which runs odd jobs on behalf of client applications
License: BSD
Group:	System/Configuration/Other
BuildRequires:	dbus-devel >= 0.22, selinux-devel, libxml2-devel
BuildRequires:	pam-devel, python-devel, pkgconfig
BuildRequires:	sasl-devel, krb5-devel, openldap-devel
BuildRequires:	docbook-dtds, xmlto, autoconf, automake, libtool
Requires(post): /sbin/service
Requires(postun): /sbin/service
Requires(post): /sbin/chkconfig
Requires(pre): /sbin/chkconfig
Obsoletes: oddjob-devel < 0.30, oddjob-libs < 0.30, oddjob-python < 0.30
URL: http://www.fedorahosted.org/oddjob

%description
oddjob is a D-BUS service which performs particular tasks for clients which
connect to it and issue requests using the system-wide message bus.

%package mkhomedir
Group: System/Servers
Summary: An oddjob helper which creates and populates home directories
Requires: %{name} = %{version}-%{release}
Requires(post): %{dbus_send}, grep, sed

%description mkhomedir
This package contains the oddjob helper which can be used by the
pam_oddjob_mkhomedir module to create a home directory for a user
at login-time.

%package sample
Group: System/Servers
Summary: A sample oddjob service.
Requires: %{name} = %{version}-%{release}

%description sample
This package contains a trivial sample oddjob service.

%prep
%setup -q
%patch0 -p1 -b .noclose
%patch1 -p1 -b .umasks
%patch2 -p1 -b .tests
%patch3 -p1 -b .init-status
autoreconf -f -i

%build
sample_flag=
%if %{build_sample_subpackage}
sample_flag=--enable-sample
%endif
%configure \
	--disable-static \
	--with-selinux-acls \
	--with-selinux-labels \
	--without-python --enable-xml-docs --enable-compat-dtd \
	--disable-dependency-tracking \
	$sample_flag
make %{_smp_mflags}

%install
rm -fr "$RPM_BUILD_ROOT"
make install DESTDIR="$RPM_BUILD_ROOT"
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/security/*.la
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/security/*.a
if ! test -d "$RPM_BUILD_ROOT"/%{_lib}/security ; then
	mkdir -p "$RPM_BUILD_ROOT"/%{_lib}/security
	mv "$RPM_BUILD_ROOT"/%{_libdir}/security/*.so "$RPM_BUILD_ROOT"/%{_lib}/security/
fi
# Recommended, though I disagree.
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/*.la

%if ! %{build_sample_subpackage}
# Go ahead and build the sample layout.
mkdir -p sample-install-root/sample/{%{_sysconfdir}/{dbus-1/system.d,%{name}d.conf.d},%{_libdir}/%{name}}
install -m644 sample/oddjobd-sample.conf	sample-install-root/sample/%{_sysconfdir}/%{name}d.conf.d/
install -m644 sample/oddjob-sample.conf		sample-install-root/sample/%{_sysconfdir}/dbus-1/system.d/
install -m755 sample/oddjob-sample.sh		sample-install-root/sample/%{_libdir}/%{name}/
%endif

# Make sure we don't needlessly make these docs executable.
chmod -x src/reload src/mkhomedirfor src/mkmyhomedir

# Make sure the datestamps match in multilib pairs.
touch -r src/oddjobd-mkhomedir.conf.in	$RPM_BUILD_ROOT/%{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf
touch -r src/oddjob-mkhomedir.conf.in	$RPM_BUILD_ROOT/%{_sysconfdir}/dbus-1/system.d/oddjob-mkhomedir.conf

%clean
rm -fr "$RPM_BUILD_ROOT"

%files
%defattr(-,root,root,-)
%doc *.dtd COPYING NEWS QUICKSTART doc/oddjob.html src/reload
%if ! %{build_sample_subpackage}
%doc sample-install-root/sample
%endif
%{_initrddir}/oddjobd
%{_bindir}/*
%{_sbindir}/*
%config(noreplace) %{_sysconfdir}/dbus-*/system.d/oddjob.conf
%config(noreplace) %{_sysconfdir}/oddjobd.conf
%dir %{_sysconfdir}/oddjobd.conf.d
%config(noreplace) %{_sysconfdir}/oddjobd.conf.d/oddjobd-introspection.conf
%dir %{_sysconfdir}/%{name}
%dir %{_libexecdir}/%{name}
%{_libexecdir}/%{name}/sanity.sh
%{_mandir}/*/oddjob*.*

%files mkhomedir
%defattr(-,root,root)
%doc src/mkhomedirfor src/mkmyhomedir
%dir %{_libexecdir}/%{name}
%{_libexecdir}/%{name}/mkhomedir
/%{_lib}/security/pam_oddjob_mkhomedir.so
%{_mandir}/*/pam_oddjob_mkhomedir.*
%config(noreplace) %{_sysconfdir}/dbus-*/system.d/oddjob-mkhomedir.conf
%config(noreplace) %{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf

%if %{build_sample_subpackage}
%files sample
%defattr(-,root,root)
%{_libdir}/%{name}/oddjob-sample.sh
%config %{_sysconfdir}/dbus-*/system.d/oddjob-sample.conf
%config %{_sysconfdir}/oddjobd.conf.d/oddjobd-sample.conf
%endif

%post
if test $1 -eq 1 ; then
	killall -HUP dbus-daemon 2>&1 > /dev/null
fi
/sbin/chkconfig --add oddjobd

%postun
if [ $1 -gt 0 ] ; then
	/sbin/service oddjobd condrestart 2>&1 > /dev/null || :
fi
exit 0

%preun
if [ $1 -eq 0 ] ; then
	/sbin/service oddjobd stop > /dev/null 2>&1
	/sbin/chkconfig --del oddjobd
fi

%post mkhomedir
# Adjust older configuration files that may have been modified so that they
# point to the current location of the helper.
cfg=%{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf
if grep -q %{_libdir}/%{name}/mkhomedir $cfg ; then
	sed -i 's^%{_libdir}/%{name}/mkhomedir^%{_libexecdir}/%{name}/mkhomedir^g' $cfg
fi
if test $1 -eq 1 ; then
	killall -HUP dbus-daemon 2>&1 > /dev/null
fi
if [ -f /var/lock/subsys/oddjobd ] ; then
	%{dbus_send} --system --dest=com.redhat.oddjob /com/redhat/oddjob com.redhat.oddjob.reload
fi
exit 0

