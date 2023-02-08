Name:      observatory-efafocus-client
Version:   20230208
Release:   0
Url:       https://github.com/warwick-one-metre/efafocusd
Summary:   Planewave focuser control client.
License:   GPL-3.0
Group:     Unspecified
BuildArch: noarch
Requires:  python3 python3-Pyro4 python3-warwick-observatory-common python3-warwick-observatory-efafocus

%description

%build
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}/etc/bash_completion.d
%{__install} %{_sourcedir}/focus %{buildroot}%{_bindir}
%{__install} %{_sourcedir}/completion/focus %{buildroot}/etc/bash_completion.d/focus

%files
%defattr(0755,root,root,-)
%{_bindir}/focus
/etc/bash_completion.d/focus

%changelog
