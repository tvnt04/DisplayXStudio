Name:           display-x-studio
Version:        0.0.0
Release:        1%{?dist}
Summary:        Display X Studio

License:        Proprietary
URL:            https://github.com/tvnt04/DisplayXStudio

BuildArch:      x86_64

%description
Display X Studio multispectral display and analysis application.

%install
mkdir -p %{buildroot}/opt/display-x-studio
cp -a %{_sourcedir}/Display-X-Studio/. \
    %{buildroot}/opt/display-x-studio/

mkdir -p %{buildroot}/usr/bin
cat > %{buildroot}/usr/bin/display-x-studio <<'SCRIPT'
#!/bin/sh
exec "/opt/display-x-studio/Display X Studio" "$@"
SCRIPT
chmod 0755 %{buildroot}/usr/bin/display-x-studio

mkdir -p %{buildroot}/usr/share/applications
cat > %{buildroot}/usr/share/applications/display-x-studio.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Display X Studio
Comment=Display X Studio
Exec=display-x-studio
Icon=display-x-studio
Categories=Graphics;
Terminal=false
StartupWMClass=Display X Studio
DESKTOP

mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
cp %{_sourcedir}/display-x-studio.png \
    %{buildroot}/usr/share/icons/hicolor/256x256/apps/display-x-studio.png

%files
/opt/display-x-studio
/usr/bin/display-x-studio
/usr/share/applications/display-x-studio.desktop
/usr/share/icons/hicolor/256x256/apps/display-x-studio.png

%changelog
* Wed Aug 19 2026 Display X Studio Team - 0.0.0-1
- Initial RPM package
