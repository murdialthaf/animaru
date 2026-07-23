# Maintainer: Murdi <murdi@example.com>
# Contributor: Murdi
# Arch: any

pkgname=animaru
pkgver=0.1.0
pkgrel=1
pkgdesc="A GTK4 GUI for watching and downloading anime"
arch=('any')
url="https://github.com/murdi/animaru"
license=('GPL3')
depends=(
  'python'
  'python-gobject'
  'gtk4'
  'libadwaita'
  'mpv'
)
makedepends=(
  'python-build'
  'python-installer'
  'python-wheel'
  'python-setuptools'
)

# anipy-api is on PyPI but not yet in the AUR.
# It will be pulled via pip during the build.
# Once it's available in the AUR, add 'python-anipy-api' to depends
# and remove the pip install from prepare().
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/murdi/${pkgname}/archive/v${pkgver}.tar.gz")
sha256sums=('SKIP')

prepare() {
  cd "${srcdir}/${pkgname}-${pkgver}"
  pip install --user anipy-api
}

build() {
  cd "${srcdir}/${pkgname}-${pkgver}"
  python -m build --wheel --no-isolation
}

package() {
  cd "${srcdir}/${pkgname}-${pkgver}"
  python -m installer --destdir="${pkgdir}" dist/*.whl

  install -Dm644 data/animaru.desktop -t "${pkgdir}/usr/share/applications"
  install -Dm644 data/icons/animaru.svg -t "${pkgdir}/usr/share/icons/hicolor/scalable/apps"
}
