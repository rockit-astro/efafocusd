Name:      halfmetre-efafocusd-data
Version:   20230205
Release:   0
Url:       https://github.com/warwick-one-metre/efafocusd
Summary:   Focuser configuration files.
License:   GPL-3.0
Group:     Unspecified
BuildArch: noarch

%description

%build
mkdir -p %{buildroot}%{_udevrulesdir}
mkdir -p %{buildroot}%{_sysconfdir}/focusd/

%{__install} %{_sourcedir}/10-halfmetre-focuser.rules %{buildroot}%{_udevrulesdir}
%{__install} %{_sourcedir}/halfmetre.json %{buildroot}%{_sysconfdir}/focusd/

%files
%defattr(0644,root,root,-)
%{_udevrulesdir}/10-halfmetre-focuser.rules
%{_sysconfdir}/focusd/halfmetre.json

%changelog
