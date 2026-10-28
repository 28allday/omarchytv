#!/bin/sh
# OmarchyTV start-up and Home-button helper for ROOTED LG webOS TVs (Homebrew Channel).
#
# OmarchyTV installs this from All settings; nothing here runs on unrooted TVs.
# Homebrew Channel runs /var/lib/webosbrew/init.d/omarchytv at boot, which starts this script.
# Behaviour is driven by flag files in /var/lib/omarchytv/ (the settings toggles create/remove them):
#   boot  open OmarchyTV once the TV has started
#   home  when LG Home comes to the front, open OmarchyTV instead. Pressing Home while
#         OmarchyTV is already in front still shows LG Home, so LG's own menus stay reachable.
# With neither flag present the script exits.
APP=com.omarchytv.home
LG_HOME=com.webos.app.home
FLAGS=/var/lib/omarchytv
PIDFILE=/tmp/omarchytv-home.pid
LOG=/tmp/omarchytv-home.log

[ -f "$FLAGS/boot" ] || [ -f "$FLAGS/home" ] || exit 0
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then exit 0; fi
echo $$ > "$PIDFILE"

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
# luna-send prints nothing without a TTY; script(1) provides one.
luna() { script -q -c "luna-send $*" /dev/null; }
launch() { luna -n 1 luna://com.webos.service.applicationmanager/launch "'{\"id\":\"$APP\"}'" >/dev/null; }
screen_on() {
    p=$(luna -n 1 luna://com.webos.service.tvpower/power/getPowerState "'{}'")
    echo "$p" | grep -q '"Active"' && ! echo "$p" | grep -q 'Screen Off'
}

if [ "$1" != "--no-boot" ] && [ -f "$FLAGS/boot" ]; then
    n=0
    until luna -n 1 luna://com.webos.service.applicationmanager/getForegroundAppInfo "'{}'" | grep -q '"returnValue":true'; do
        n=$((n + 1)); [ $n -gt 120 ] && break; sleep 2
    done
    sleep 5
    screen_on && { log "boot: opening $APP"; launch; }
fi

while [ -f "$FLAGS/home" ]; do
    prev=""
    luna -i luna://com.webos.service.applicationmanager/getForegroundAppInfo "'{\"subscribe\":true}'" |
    while IFS= read -r line; do
        [ -f "$FLAGS/home" ] || exit 0
        app=$(echo "$line" | sed -n 's/.*"appId":"\([^"]*\)".*/\1/p')
        [ -z "$app" ] && continue
        if [ "$app" = "$LG_HOME" ] && [ "$prev" != "$APP" ] && screen_on; then
            log "Home pressed in '$prev': opening $APP"
            launch
        fi
        prev=$app
    done
    sleep 3
done
log "home redirect off, exiting"
rm -f "$PIDFILE"
