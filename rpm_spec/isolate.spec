%define name isolate
%define version 1.3
%define release 1
%define boxdir %{_sharedstatedir}/%{name}
%define confdir %{_sysconfdir}/%{name}
%define conffile %{confdir}/default.cf

Summary: Isolate sandbox built for safely running untrusted executables
Name: %{name}
Version: %{version}
Release: %{release}
Source0: https://github.com/ioi/%{name}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
License: GPLv2+
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Url: https://github.com/ioi/isolate
BuildRequires: asciidoc

%description
Isolate is a sandbox built to safely run untrusted executables, offering them a
limited-access environment and preventing them from affecting the host system.
It takes advantage of features specific to the Linux kernel, like namespaces
and control groups.

%prep
%autosetup -n %{name}-%{version}

%build
%make_build BINDIR=%{_bindir} CONFIG=%{conffile}

%install
%make_install BINDIR=%{buildroot}/%{_bindir} CONFIG=%{buildroot}/%{conffile}
make install-doc MANDIR=%{buildroot}/%{_mandir}
mkdir -p %{buildroot}/%{boxdir}

%clean
make clean

%post

%postun

%pre

%preun

%files
%defattr(-,root,root)
%dir %{confdir}
%dir %{boxdir}

%{_bindir}/%{name}
%config(noreplace) %{conffile}
%{_mandir}/man1/%{name}.1.gz

%changelog

