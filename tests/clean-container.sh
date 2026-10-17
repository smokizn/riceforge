#!/usr/bin/env bash
# Install Riceforge into a brand-new Arch Linux container, as a fresh user, with
# real pacman. Proves the official-repo dependency list, deployment and theme
# verification work from nothing. It cannot test: systemd services, a display
# manager, a graphical login, or AUR builds.
#
#   tests/clean-container.sh            # official packages only (~1.5 GB download)
#   FEATURES=core tests/clean-container.sh
#
# Needs docker (or podman via DOCKER=podman). Changes nothing on the host except a
# docker volume "riceforge-pkg-cache" (pacman cache; remove: docker volume rm riceforge-pkg-cache).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
DOCKER="${DOCKER:-docker}"
IMAGE="${IMAGE:-archlinux:latest}"
FEATURES="${FEATURES:-core,shell,apps,aesthetic}"
LOG="${LOG:-$REPO/tests/.sandbox/clean-container.log}"
mkdir -p "$(dirname "$LOG")"

# ship the working tree as a tarball (what a fresh clone would contain + local plates excluded)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git -C "$REPO" ls-files -co --exclude-standard -z | tar -C "$REPO" --null -T - -czf "$tmp/riceforge.tgz"

"$DOCKER" run --rm -i -v "$tmp:/src:ro" -v riceforge-pkg-cache:/var/cache/pacman/pkg -e FEATURES="$FEATURES" "$IMAGE" bash -s <<'EOF' 2>&1 | tee "$LOG"
set -euo pipefail
echo "== container: $(. /etc/os-release; echo "$PRETTY_NAME") $(uname -m)"
pacman -Syu --noconfirm --needed sudo git >/dev/null
useradd -m -G wheel tester
echo '%wheel ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers.d/wheel
# container images strip docs/locales; keep fonts, licences and icons installing normally
sed -i 's/^NoExtract/#NoExtract/' /etc/pacman.conf
ln -sf /usr/share/zoneinfo/Europe/Berlin /etc/localtime
su - tester -c '
set -e
mkdir -p ~/src && tar -C ~/src -xzf /src/riceforge.tgz && mv ~/src ~/riceforge
cd ~/riceforge
echo "== ./setup (clone at ~/riceforge, not ~/.config/riceforge)"
./setup --yes --no-system --profile desktop --features "'"$FEATURES"'" --aur-helper none
echo "== rerun (must change nothing)"
./setup --yes --no-system --no-packages --profile desktop --features "'"$FEATURES"'" --aur-helper none | grep -E "deployed|changed"
echo "== doctor"
~/.local/bin/riceforge doctor || true
echo "== Hyprland --verify-config (XDG_RUNTIME_DIR as a login would set it)"
export XDG_RUNTIME_DIR=$(mktemp -d)
Hyprland --verify-config -c ~/.config/hypr/hyprland.lua 2>&1 | tail -1
echo "== theme switch"
for t in etch original nacre; do RICEFORGE_NO_LIVE=1 ~/.local/bin/riceforge apply $t | tail -1; done
echo "== uninstall"
~/.local/bin/riceforge uninstall --yes | tail -3
'
EOF
echo "log: $LOG"
