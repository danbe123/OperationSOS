#!/usr/bin/env bash
# Operation SOS installer (spec section 13).
#
#   sudo install/install.sh [--dry-run] [--dev] [--skip-llama] [--with-jellyfin] [--pcie-gen3]
#
# Runs as root on a fresh 64-bit Raspberry Pi OS Lite (Trixie) booted from the NVMe. Idempotent: every
# step is a function that reports "unchanged" when its result already exists, so a second run makes no
# changes. --dry-run prints every step and the files it would write, touches nothing and needs no root.
# --dev (on a PC) skips the hotspot, mount, backlight, kiosk and boot steps. --skip-llama skips the
# llama.cpp build, --with-jellyfin installs Jellyfin, --pcie-gen3 enables PCIe Gen 3 in the boot fragment.
# Overrides used by the tests: SOS_ARCH (default: uname -m), SOS_WEB_DIST (default: <repo>/web/dist).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$SCRIPT_DIR/.." && pwd)
ARCH=${SOS_ARCH:-$(uname -m)}
WEB_DIST=${SOS_WEB_DIST:-$REPO/web/dist}

PREFIX=/srv/sos
SOS_USER=sos
SOS_HOME=/home/sos
BUILD_DIR=$PREFIX/build
BOOT_DIR=/boot/firmware
UNIT_DIR=/etc/systemd/system
NM_DIR=/etc/NetworkManager
# python3-dev is the one addition to the spec's list: hnswlib (the household semantic index) ships no
# wheels, so step_venv's `pip install -e $PREFIX/api` compiles it here and needs Python.h as well as
# cmake and build-essential.
APT_PACKAGES="network-manager dnsmasq-base avahi-daemon cage wlr-randr chromium python3-venv python3-dev aria2 cmake build-essential poppler-utils"
# Not in the spec's list but needed by this script: git (llama.cpp clone), curl (downloads), rsync (copies).
APT_EXTRA="git curl rsync"
CMAKE_CONFIGURE=(cmake -S . -B build -DGGML_NATIVE=ON -DGGML_CPU_KLEIDIAI=ON -DLLAMA_BUILD_TESTS=OFF)
CMAKE_BUILD=(cmake --build build --config Release -j4)
CMAKE_INSTALL=(cmake --install build --prefix /usr/local)

DRY_RUN=0
DEV=0
SKIP_LLAMA=0
WITH_JELLYFIN=0
PCIE_GEN3=0
CHANGED=0

# shellcheck disable=SC1091
. "$SCRIPT_DIR/versions.env"

usage() { sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --dev) DEV=1 ;;
    --skip-llama) SKIP_LLAMA=1 ;;
    --with-jellyfin) WITH_JELLYFIN=1 ;;
    --pcie-gen3) PCIE_GEN3=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "install.sh: unknown option '$arg'" >&2; usage >&2; exit 2 ;;
  esac
done

case "$ARCH" in
  aarch64) KIWIX_ARCH=aarch64; CADDY_ARCH=arm64 ;;
  x86_64) KIWIX_ARCH=x86_64; CADDY_ARCH=amd64 ;;
  *) echo "install.sh: unsupported architecture '$ARCH' (aarch64 or x86_64)" >&2; exit 2 ;;
esac
KIWIX_URL="$KIWIX_TOOLS_BASE/kiwix-tools_linux-${KIWIX_ARCH}-${KIWIX_TOOLS}.tar.gz"
CADDY_URL="$CADDY_BASE/v${CADDY}/caddy_${CADDY}_linux_${CADDY_ARCH}.tar.gz"

if [ "$DRY_RUN" = 0 ] && [ "$(id -u)" != 0 ]; then
  echo "install.sh: run as root (or use --dry-run)" >&2
  exit 1
fi

# --- helpers ---------------------------------------------------------------------------------------

say()    { printf 'step %s: %s\n' "$1" "$2"; }
would()  { printf 'step %s: would %s\n' "$1" "$2"; }
rel()    { printf '%s' "${1#"$REPO/"}"; }
as_sos() { runuser -u "$SOS_USER" -- "$@"; }

# install_file <src> <dest> <mode> [owner:group]: copy when different. Returns 0 when it wrote and 1 when
# the destination already matched. In a dry run it only prints the destination and returns 0.
install_file() {
  local src=$1 dest=$2 mode=$3 owner=${4:-root:root}
  if [ "$DRY_RUN" = 1 ]; then
    printf '  write %s (from %s, mode %s, %s)\n' "$dest" "$(rel "$src")" "$mode" "$owner"
    return 0
  fi
  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    return 1
  fi
  install -D -m "$mode" -o "${owner%%:*}" -g "${owner##*:}" "$src" "$dest"
  CHANGED=1
  return 0
}

# sync_tree <src-dir> <dest-dir>: rsync owned by sos; returns 0 when anything changed, 1 when identical.
sync_tree() {
  local out
  out=$(rsync -ai --delete --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
    --chown="$SOS_USER:$SOS_USER" "$1/" "$2/")
  [ -n "$out" ]
}

# --- steps (spec section 13, in order) -------------------------------------------------------------

step_apt() {
  local pkgs="$APT_PACKAGES $APT_EXTRA" missing="" p
  if [ "$DRY_RUN" = 1 ]; then would apt "apt-get install $pkgs"; return; fi
  for p in $pkgs; do
    dpkg -s "$p" >/dev/null 2>&1 || missing="$missing $p"
  done
  if [ -z "$missing" ]; then say apt unchanged; return; fi
  apt-get update -q
  # shellcheck disable=SC2086
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q $missing
  CHANGED=1
  say apt "installed$missing"
}

step_downloads() {
  local tmp changed=0
  if [ "$DRY_RUN" = 1 ]; then
    would downloads "fetch $KIWIX_URL -> /usr/local/bin/kiwix-serve, /usr/local/bin/kiwix-manage, /usr/local/bin/kiwix-search"
    would downloads "fetch $CADDY_URL -> /usr/local/bin/caddy"
    return
  fi
  if ! /usr/local/bin/kiwix-serve --version 2>/dev/null | grep -q "^kiwix-tools $KIWIX_TOOLS\$"; then
    tmp=$(mktemp -d)
    curl -fsSL "$KIWIX_URL" | tar -xz -C "$tmp"
    install -m 755 "$tmp"/kiwix-tools_*/kiwix-serve "$tmp"/kiwix-tools_*/kiwix-manage "$tmp"/kiwix-tools_*/kiwix-search /usr/local/bin/
    rm -rf "$tmp"
    changed=1
  fi
  if ! /usr/local/bin/caddy version 2>/dev/null | grep -q "^v$CADDY "; then
    tmp=$(mktemp -d)
    curl -fsSL "$CADDY_URL" | tar -xz -C "$tmp" caddy
    install -m 755 "$tmp/caddy" /usr/local/bin/caddy
    rm -rf "$tmp"
    changed=1
  fi
  if [ "$changed" = 1 ]; then CHANGED=1; say downloads "installed kiwix-tools $KIWIX_TOOLS and caddy $CADDY"; else say downloads unchanged; fi
}

step_llama() {
  local src=$BUILD_DIR/llama.cpp marker head
  marker=$BUILD_DIR/llama.cpp/.sos-installed-$LLAMA_CPP_TAG
  if [ "$SKIP_LLAMA" = 1 ]; then say llama "skipped (--skip-llama)"; return; fi
  if [ "$DRY_RUN" = 1 ]; then
    would llama "clone $LLAMA_CPP_REPO at $LLAMA_CPP_TAG into $src, run '${CMAKE_CONFIGURE[*]} && ${CMAKE_BUILD[*]}' then '${CMAKE_INSTALL[*]}' -> /usr/local/bin/llama-server"
    return
  fi
  if [ -x /usr/local/bin/llama-server ] && [ -f "$marker" ]; then say llama unchanged; return; fi
  if [ ! -d "$src/.git" ]; then
    git clone --depth 1 --branch "$LLAMA_CPP_TAG" "$LLAMA_CPP_REPO" "$src"
  fi
  head=$(git -C "$src" rev-parse HEAD)
  if [ "$head" != "$LLAMA_CPP_COMMIT" ]; then
    echo "install.sh: warning: $LLAMA_CPP_TAG resolved to $head; versions.env expects $LLAMA_CPP_COMMIT" >&2
  fi
  (cd "$src" && "${CMAKE_CONFIGURE[@]}" && "${CMAKE_BUILD[@]}" && "${CMAKE_INSTALL[@]}")
  ldconfig
  touch "$marker"
  CHANGED=1
  say llama "built and installed llama-server ($LLAMA_CPP_TAG)"
}

step_jellyfin() {
  local version codename
  if [ "$DRY_RUN" = 1 ]; then
    would jellyfin "add $JELLYFIN_REPO (keyring /etc/apt/keyrings/jellyfin.gpg, /etc/apt/sources.list.d/jellyfin.sources) and apt-get install jellyfin $JELLYFIN (library root $PREFIX/extended/media)"
    return
  fi
  if dpkg-query -W -f '${Version}' jellyfin 2>/dev/null | grep -q "^$JELLYFIN"; then say jellyfin unchanged; return; fi
  install -d -m 755 /etc/apt/keyrings
  curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/jellyfin.gpg
  # shellcheck disable=SC1091
  codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
  cat > /etc/apt/sources.list.d/jellyfin.sources <<EOF
Types: deb
URIs: $JELLYFIN_REPO
Suites: $codename
Components: main
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/jellyfin.gpg
EOF
  apt-get update -q
  version=$(apt-cache madison jellyfin | awk -v v="$JELLYFIN" '$3 ~ "^"v { print $3; exit }')
  if [ -z "$version" ]; then echo "install.sh: jellyfin $JELLYFIN is not in $JELLYFIN_REPO for $codename" >&2; exit 1; fi
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q "jellyfin=$version"
  CHANGED=1
  say jellyfin "installed jellyfin $version (point its library at $PREFIX/extended/media; not together with the AI on 8GB)"
}

step_user() {
  local changed=0 g
  if [ "$DRY_RUN" = 1 ]; then would user "create user $SOS_USER (home $SOS_HOME, groups video input render)"; return; fi
  if ! id "$SOS_USER" >/dev/null 2>&1; then
    useradd --create-home --home-dir "$SOS_HOME" --shell /bin/bash "$SOS_USER"
    changed=1
  fi
  for g in video input render; do
    if getent group "$g" >/dev/null && ! id -nG "$SOS_USER" | tr ' ' '\n' | grep -qx "$g"; then
      usermod -aG "$g" "$SOS_USER"
      changed=1
    fi
  done
  if [ "$changed" = 1 ]; then CHANGED=1; say user "created or updated $SOS_USER"; else say user unchanged; fi
}

step_tree() {
  local d changed=0
  local dirs="core/zim core/maps core/docs core/models extended state/config state/playbooks state/manifest web api build"
  if [ "$DRY_RUN" = 1 ]; then
    would tree "create $PREFIX/{${dirs// /,}} owned by $SOS_USER"
    printf '  write %s (SOS_MODEL default for sos-llama.service, if absent)\n' "$PREFIX/state/config/ai.env"
    return
  fi
  for d in $dirs; do
    if [ ! -d "$PREFIX/$d" ]; then install -d -o "$SOS_USER" -g "$SOS_USER" "$PREFIX/$d"; changed=1; fi
  done
  if [ ! -f "$PREFIX/state/config/ai.env" ]; then
    echo "SOS_MODEL=gemma-4-E2B-it-Q4_K_M.gguf" > "$PREFIX/state/config/ai.env"
    chown "$SOS_USER:$SOS_USER" "$PREFIX/state/config/ai.env"
    changed=1
  fi
  if [ "$changed" = 1 ]; then CHANGED=1; say tree "created $PREFIX tree"; else say tree unchanged; fi
}

step_venv() {
  local changed=0
  if [ "$DRY_RUN" = 1 ]; then would venv "copy api/ -> $PREFIX/api and pip install the sos package into $PREFIX/api/.venv"; return; fi
  if sync_tree "$REPO/api" "$PREFIX/api"; then changed=1; fi
  if [ ! -x "$PREFIX/api/.venv/bin/python" ]; then
    as_sos python3 -m venv "$PREFIX/api/.venv"
    changed=1
  fi
  if [ "$changed" = 0 ]; then say venv unchanged; return; fi
  as_sos "$PREFIX/api/.venv/bin/pip" install -q --upgrade pip
  as_sos "$PREFIX/api/.venv/bin/pip" install -q -e "$PREFIX/api"
  CHANGED=1
  say venv "installed the sos package into $PREFIX/api/.venv"
}

step_web() {
  local src note=""
  if [ -f "$WEB_DIST/index.html" ]; then src=$WEB_DIST; else src=$SCRIPT_DIR/placeholder; note=" (web/dist absent, placeholder used)"; fi
  if [ "$DRY_RUN" = 1 ]; then would web "copy $(rel "$src") -> $PREFIX/web$note"; return; fi
  if sync_tree "$src" "$PREFIX/web"; then CHANGED=1; say web "installed $(rel "$src") -> $PREFIX/web$note"; else say web unchanged; fi
}

step_units() {
  local unit changed=0
  if [ "$DRY_RUN" = 1 ]; then would units "write the systemd units and daemon-reload"; fi
  for unit in caddy.service kiwix-serve.service sos-api.service sos-llama.service sos-embed.service sos-kiosk.service; do
    if install_file "$SCRIPT_DIR/systemd/$unit" "$UNIT_DIR/$unit" 644; then changed=1; fi
  done
  if [ "$DRY_RUN" = 1 ]; then return; fi
  if [ "$changed" = 1 ]; then systemctl daemon-reload; say units updated; else say units unchanged; fi
}

step_caddy() {
  if [ "$DRY_RUN" = 1 ]; then would caddy "write the Caddyfile"; install_file "$SCRIPT_DIR/caddy/Caddyfile" /etc/caddy/Caddyfile 644; return; fi
  if install_file "$SCRIPT_DIR/caddy/Caddyfile" /etc/caddy/Caddyfile 644; then
    if systemctl is-active -q caddy.service; then systemctl reload caddy.service; fi
    say caddy "updated /etc/caddy/Caddyfile"
  else
    say caddy unchanged
  fi
}

step_hotspot() {
  local f changed=0
  if [ "$DEV" = 1 ]; then say hotspot "skipped (--dev)"; return; fi
  if [ "$DRY_RUN" = 1 ]; then would hotspot "write the NetworkManager profiles and the dnsmasq name catch-all, then nmcli connection reload"; fi
  for f in sos-hotspot sos-eth-client sos-eth-direct; do
    if install_file "$SCRIPT_DIR/nm/$f.nmconnection" "$NM_DIR/system-connections/$f.nmconnection" 600; then changed=1; fi
  done
  if install_file "$SCRIPT_DIR/nm/dnsmasq-shared.d/sos.conf" "$NM_DIR/dnsmasq-shared.d/sos.conf" 644; then changed=1; fi
  if [ "$DRY_RUN" = 1 ]; then return; fi
  if [ "$changed" = 1 ]; then nmcli connection reload; say hotspot "updated NetworkManager profiles"; else say hotspot unchanged; fi
}

step_mount() {
  local unit changed=0
  if [ "$DEV" = 1 ]; then say mount "skipped (--dev)"; return; fi
  if [ "$DRY_RUN" = 1 ]; then would mount "write the external-drive mount and rescan units and daemon-reload"; fi
  for unit in srv-sos-extended.mount sos-extended-rescan.service; do
    if install_file "$SCRIPT_DIR/systemd/$unit" "$UNIT_DIR/$unit" 644; then changed=1; fi
  done
  if [ "$DRY_RUN" = 1 ]; then return; fi
  if [ "$changed" = 1 ]; then systemctl daemon-reload; say mount updated; else say mount unchanged; fi
}

step_backlight() {
  if [ "$DEV" = 1 ]; then say backlight "skipped (--dev)"; return; fi
  if [ "$DRY_RUN" = 1 ]; then would backlight "write the udev rule and reload udev"; install_file "$SCRIPT_DIR/udev/90-sos-backlight.rules" /etc/udev/rules.d/90-sos-backlight.rules 644; return; fi
  if install_file "$SCRIPT_DIR/udev/90-sos-backlight.rules" /etc/udev/rules.d/90-sos-backlight.rules 644; then
    udevadm control --reload-rules
    udevadm trigger --subsystem-match=backlight --action=add
    say backlight updated
  else
    say backlight unchanged
  fi
}

step_sudoers() {
  if [ "$DRY_RUN" = 1 ]; then would sudoers "check with visudo -cf and write the sudoers rule"; install_file "$SCRIPT_DIR/sudoers/sos" /etc/sudoers.d/sos 440; return; fi
  visudo -cf "$SCRIPT_DIR/sudoers/sos" >/dev/null
  if install_file "$SCRIPT_DIR/sudoers/sos" /etc/sudoers.d/sos 440; then say sudoers updated; else say sudoers unchanged; fi
}

step_kiosk() {
  local changed=0 env=$PREFIX/state/config/kiosk.env
  if [ "$DEV" = 1 ]; then say kiosk "skipped (--dev)"; return; fi
  if [ "$DRY_RUN" = 1 ]; then
    would kiosk "install the kiosk wrapper, write $env (SOS_KIOSK_TRANSFORM=90) if absent, systemctl set-default graphical.target"
    install_file "$SCRIPT_DIR/kiosk/sos-kiosk-app" /usr/local/bin/sos-kiosk-app 755
    return
  fi
  if install_file "$SCRIPT_DIR/kiosk/sos-kiosk-app" /usr/local/bin/sos-kiosk-app 755; then changed=1; fi
  if [ ! -f "$env" ]; then printf 'SOS_KIOSK_TRANSFORM=90\n' > "$env"; chown "$SOS_USER:$SOS_USER" "$env"; changed=1; fi
  if [ "$(systemctl get-default)" != graphical.target ]; then systemctl set-default graphical.target; changed=1; fi
  if [ "$changed" = 1 ]; then CHANGED=1; say kiosk updated; else say kiosk unchanged; fi
}

step_boot() {
  local tmp gen3="" changed=0
  if [ "$DEV" = 1 ]; then say boot "skipped (--dev)"; return; fi
  if [ "$PCIE_GEN3" = 1 ]; then gen3=" with dtparam=pciex1_gen=3 enabled (--pcie-gen3)"; fi
  if [ "$DRY_RUN" = 1 ]; then
    would boot "write $BOOT_DIR/sos.txt from install/boot/config.txt.d/sos.txt$gen3 and add 'include sos.txt' to $BOOT_DIR/config.txt"
    return
  fi
  tmp=$(mktemp)
  if [ "$PCIE_GEN3" = 1 ]; then
    sed 's/^#dtparam=pciex1_gen=3/dtparam=pciex1_gen=3/' "$SCRIPT_DIR/boot/config.txt.d/sos.txt" > "$tmp"
  else
    cp "$SCRIPT_DIR/boot/config.txt.d/sos.txt" "$tmp"
  fi
  # /boot/firmware is vfat, so plain cp instead of install (no ownership there).
  if ! cmp -s "$tmp" "$BOOT_DIR/sos.txt"; then cp "$tmp" "$BOOT_DIR/sos.txt"; changed=1; fi
  rm -f "$tmp"
  if ! grep -qx 'include sos.txt' "$BOOT_DIR/config.txt"; then printf '\ninclude sos.txt\n' >> "$BOOT_DIR/config.txt"; changed=1; fi
  if [ "$changed" = 1 ]; then CHANGED=1; say boot "updated $BOOT_DIR/sos.txt$gen3"; else say boot unchanged; fi
}

step_content() {
  local changed=0
  if [ "$DRY_RUN" = 1 ]; then would content "copy playbooks/ and manifest/ -> $PREFIX/state/ and run 'sos index' as $SOS_USER"; return; fi
  if sync_tree "$REPO/playbooks" "$PREFIX/state/playbooks"; then changed=1; fi
  if sync_tree "$REPO/manifest" "$PREFIX/state/manifest"; then changed=1; fi
  if [ "$changed" = 1 ] || [ ! -f "$PREFIX/state/sos.db" ]; then
    as_sos "$PREFIX/api/.venv/bin/sos" index
    CHANGED=1
    say content "copied playbooks and manifest, ran sos index"
  else
    say content unchanged
  fi
}

step_answers() {
  local marker=$PREFIX/state/config/answers.done pin ssid passphrase
  if [ "$DRY_RUN" = 1 ]; then would answers "prompt for the admin PIN and SSID (or read install/answers.env), then 'sos pin set' and nmcli"; return; fi
  if [ -f "$marker" ]; then say answers unchanged; return; fi
  if [ -f "$SCRIPT_DIR/answers.env" ]; then
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/answers.env"
    pin=${SOS_PIN:-}
    ssid=${SOS_SSID:-SOS}
    passphrase=${SOS_PASSPHRASE:-}
  elif [ -t 0 ]; then
    read -r -s -p "Admin PIN (4 to 12 digits, empty for none): " pin; echo
    read -r -p "Hotspot SSID [SOS]: " ssid
    ssid=${ssid:-SOS}
    read -r -s -p "Hotspot passphrase (8 to 63 characters, empty for an open network): " passphrase; echo
  else
    say answers "skipped (no install/answers.env and no terminal); run again interactively or write answers.env"
    return
  fi
  if [ -n "$pin" ]; then as_sos "$PREFIX/api/.venv/bin/sos" pin set "$pin"; fi
  SOS_SSID_VALUE=$ssid SOS_PASSPHRASE_VALUE=$passphrase as_sos "$PREFIX/api/.venv/bin/python" -c \
    'import os; from sos import db; from sos.config import get_settings; c = db.connect(get_settings().db_path); db.init_schema(c); db.set_setting(c, "ssid", os.environ["SOS_SSID_VALUE"]); db.set_setting(c, "passphrase", os.environ["SOS_PASSPHRASE_VALUE"])'
  if [ "$DEV" = 0 ]; then
    nmcli con modify sos-hotspot 802-11-wireless.ssid "$ssid"
    if [ -n "$passphrase" ]; then
      nmcli con modify sos-hotspot wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$passphrase"
    else
      nmcli con modify sos-hotspot remove wifi-sec || true
    fi
  fi
  touch "$marker"
  chown "$SOS_USER:$SOS_USER" "$marker"
  CHANGED=1
  say answers "set the admin PIN and hotspot settings"
}

step_enable() {
  local u changed=0 units="caddy.service kiwix-serve.service sos-api.service sos-embed.service avahi-daemon.service"
  if [ "$DEV" = 0 ]; then units="$units sos-kiosk.service srv-sos-extended.mount sos-extended-rescan.service"; fi
  if [ "$WITH_JELLYFIN" = 1 ]; then units="$units jellyfin.service"; fi
  if [ "$DRY_RUN" = 1 ]; then would enable "systemctl enable $units and start caddy, kiwix-serve, sos-api and avahi-daemon"; return; fi
  for u in $units; do
    if ! systemctl is-enabled -q "$u" 2>/dev/null; then systemctl enable -q "$u"; changed=1; fi
  done
  for u in caddy.service kiwix-serve.service sos-api.service avahi-daemon.service; do
    if ! systemctl is-active -q "$u"; then systemctl start "$u"; changed=1; fi
  done
  if [ "$changed" = 1 ]; then CHANGED=1; say enable "enabled and started services"; else say enable unchanged; fi
}

main() {
  local mode=""
  if [ "$DRY_RUN" = 1 ]; then mode=" --dry-run"; fi
  printf 'install.sh%s: arch %s, dev %s, skip-llama %s, with-jellyfin %s, pcie-gen3 %s\n' \
    "$mode" "$ARCH" "$DEV" "$SKIP_LLAMA" "$WITH_JELLYFIN" "$PCIE_GEN3"
  step_apt
  step_downloads
  step_llama
  if [ "$WITH_JELLYFIN" = 1 ]; then step_jellyfin; fi
  step_user
  step_tree
  step_venv
  step_web
  step_units
  step_caddy
  step_hotspot
  step_mount
  step_backlight
  step_sudoers
  step_kiosk
  step_boot
  step_content
  step_answers
  step_enable
  if [ "$DRY_RUN" = 1 ]; then echo "dry run complete: nothing was written"; return; fi
  if [ "$CHANGED" = 1 ]; then echo "install complete: changes were made; a reboot is recommended"; else echo "install complete: no changes"; fi
}

main
