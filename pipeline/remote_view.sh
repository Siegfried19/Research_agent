#!/usr/bin/env bash
# Remote view of DISPLAY :1 over Tailscale — so you can clear a Cloudflare/Duo
# challenge from your phone instead of walking to the machine.
#
# Data path:  phone browser  <--Tailscale(WireGuard, encrypted)-->  websockify
#             (noVNC web UI) <--websocket-->  x11vnc(:1, localhost only)  -->  the real Chrome
#
# Security model:
#   - x11vnc listens on localhost ONLY (raw VNC never touches the network).
#   - websockify is the only network-facing piece; it binds to THIS host's
#     Tailscale IP, so only devices on your private tailnet can reach it.
#   - VNC password (config/x11vnc.pass, gitignored) is defense-in-depth.
#   - No Tailscale Funnel: nothing is ever exposed to the public internet.
#
# Idempotent: re-running never starts duplicates. Prints the phone URL on stdout.
set -euo pipefail

DISPLAY_NUM="${REMOTE_VIEW_DISPLAY:-:1}"
VNC_PORT="${REMOTE_VIEW_VNC_PORT:-5901}"
WEB_PORT="${REMOTE_VIEW_WEB_PORT:-6080}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG_DIR="$ROOT/config"
PASS_FILE="$CFG_DIR/x11vnc.pass"      # VNC auth blob (gitignored)
PLAIN_FILE="$CFG_DIR/x11vnc.plain"    # plaintext, only to build the URL (gitignored)
# Prefer the bundled modern noVNC (pinch-zoom on phones), kept under the repo's
# big-deps folder dependencies/; fall back to the distro's old 1.0.0 (no gestures)
# if that copy isn't present.
NOVNC_WEB="$ROOT/dependencies/novnc"
[ -f "$NOVNC_WEB/vnc.html" ] || NOVNC_WEB="/usr/share/novnc"
mkdir -p "$CFG_DIR" "$ROOT/logs"

# Bind to the Tailscale IP so we never listen on the public internet / broad LAN.
TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
[ -n "$TS_IP" ] || { echo "ERROR: tailscale not up (no IP)" >&2; exit 1; }

# One-time: generate a random VNC password.
if [ ! -f "$PASS_FILE" ] || [ ! -f "$PLAIN_FILE" ]; then
  PASS="$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | head -c 12)"
  x11vnc -storepasswd "$PASS" "$PASS_FILE" >/dev/null 2>&1
  printf '%s' "$PASS" > "$PLAIN_FILE"
  chmod 600 "$PASS_FILE" "$PLAIN_FILE"
fi
PASS="$(cat "$PLAIN_FILE")"

# x11vnc on :1, localhost-only, password-protected. -forever: survive disconnects.
if ! pgrep -f "x11vnc.*-rfbport $VNC_PORT" >/dev/null 2>&1; then
  x11vnc -display "$DISPLAY_NUM" -rfbauth "$PASS_FILE" \
    -localhost -rfbport "$VNC_PORT" \
    -forever -shared -noxdamage -bg -o "$ROOT/logs/x11vnc.log" >/dev/null 2>&1
fi

# websockify: serve noVNC web UI + proxy websocket -> localhost VNC, bound to tailnet IP.
if ! pgrep -f "websockify.*:$WEB_PORT" >/dev/null 2>&1; then
  setsid websockify --web "$NOVNC_WEB" "$TS_IP:$WEB_PORT" "localhost:$VNC_PORT" \
    >"$ROOT/logs/websockify.log" 2>&1 &
  sleep 1
fi

# autoconnect + scale so the phone just shows the screen, ready to tap.
echo "http://$TS_IP:$WEB_PORT/vnc.html?host=$TS_IP&port=$WEB_PORT&path=websockify&autoconnect=true&resize=scale&password=$PASS"
