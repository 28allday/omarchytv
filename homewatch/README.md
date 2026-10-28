# OmarchyTV Home watcher (LG webOS)

On an unrooted LG TV, the remote's **Home** button always opens LG's own Home screen; no app can
take that over. The Home watcher works around this from outside the TV: it runs on an always-on
machine on your network (a NAS, a home server, a Raspberry Pi), notices when LG Home comes up, and
opens OmarchyTV in its place. Press Home and you land in OmarchyTV, like a real home screen.

Nothing on the TV is changed. Stop the watcher and the Home button works exactly as before.

## What you need

- OmarchyTV already installed on the TV ([install guide](../webos/INSTALL-WEBOS.md)).
- A machine that stays on and is on the same network as the TV, with Docker (or Python 3.10 or newer for
  the Raspberry Pi option).
- The TV's IP address, reserved in your router so it doesn't change. The TV shows it in its network
  settings (**Settings → General → Network**, then your connection).

## Set it up with Docker

Do these steps on the machine that will run the watcher, inside this `homewatch/` folder (copy the
folder over, or clone the repo there).

**1. Create your settings file**

```bash
cp .env.example .env
```

Open `.env` and set one line: `TV_IP=` followed by your TV's address, e.g. `TV_IP=192.168.1.50`.
Everything else can stay as it is.

**2. Create the folder that keeps the pairing key**

```bash
mkdir -p data && sudo chown 1000:1000 data
```

The watcher runs as user 1000 inside the container, so it needs to be able to write here. To keep
the key somewhere else (a NAS share, say), set `DATA_DIR` in `.env` to that folder and run the same
two commands on it instead.

**3. Start it**

```bash
docker compose up -d --build
```

**4. Accept the prompt on the TV**

With the TV on, a prompt appears asking to allow a new device to control the TV. Choose
**Accept**. This happens once; the key is saved to `data/client-key.json` and reused after
restarts and TV power cycles. Don't share that file; it lets anything holding it control the TV.

**5. Try it**

Open any app or input, then press **Home** on the remote. LG Home flashes up briefly and OmarchyTV
opens. To watch what the watcher is doing:

```bash
docker compose logs -f homewatch
```

You should see `event=connected` once paired, and `event=redirect` each time it sends you back to
OmarchyTV.

### Stop it or remove it

```bash
docker compose down
```

The Home button goes back to LG's normal behavior straight away. Delete the `data/` folder too if
you want the TV to ask for pairing again next time.

### Portainer

If your Docker host uses Portainer, add this as a **Stack** instead of steps 1 and 3:

- Build method: **Repository**, pointing at this repo, with compose path `homewatch/docker-compose.yml`.
- Environment variables: `TV_IP` (required) and `DATA_DIR`, set to an absolute folder on the host
  that you created as in step 2.

Then deploy the stack and accept the prompt on the TV (step 4).

## Set it up on a Raspberry Pi (no Docker)

Run these from this `homewatch/` folder on the Pi.

```bash
sudo useradd --system --home /var/lib/omarchytv-homewatch --create-home homewatch
sudo mkdir -p /opt/omarchytv-homewatch
sudo cp homewatch.py requirements.txt omarchytv-homewatch.service /opt/omarchytv-homewatch/
sudo python3 -m venv /opt/omarchytv-homewatch/.venv
sudo /opt/omarchytv-homewatch/.venv/bin/pip install -r /opt/omarchytv-homewatch/requirements.txt
```

Create `/etc/omarchytv-homewatch.env` containing your TV's address:

```ini
TV_IP=192.168.1.50
```

Install and start the service:

```bash
sudo cp /opt/omarchytv-homewatch/omarchytv-homewatch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now omarchytv-homewatch.service
```

Accept the prompt on the TV, then follow the log with
`sudo journalctl -u omarchytv-homewatch.service -f`. The pairing key is kept in
`/var/lib/omarchytv-homewatch/client-key.json`. To turn it off:
`sudo systemctl disable --now omarchytv-homewatch.service`.

## How it behaves

- It only steps in when LG Home is the app in front. Apps, inputs and OmarchyTV itself are left alone.
- It does nothing while the TV is off, in standby, or showing its screensaver.
- There is no way to reach LG Home while it runs. To use LG Home (for example to open LG's app
  store), stop the watcher, or open the app you want from OmarchyTV's Apps workspace.
- If the TV or the network drops, it reconnects on its own (retrying every few seconds, up to every
  30 seconds).
- The machine running it has to stay awake. On a laptop that sleeps, the redirect only works while
  it's awake.

## Troubleshooting

**No pairing prompt appears.** Check the TV is on and that `TV_IP` is right (the log shows
`event=reconnect` with a connection error if it can't reach the TV). Some models only accept
remote-control apps when **LG Connect Apps** / **Mobile TV On** is enabled in the TV's connection
settings.

**It paired, but pressing Home doesn't open OmarchyTV.** Your model may use a different id for LG
Home. Set `HOME_APP_IDS` in `.env` to the id your TV reports and restart, and please open an issue
with your model and webOS version so the default can cover it.

**The TV asks to pair every time.** The watcher can't write its key. Make sure the `DATA_DIR` folder
exists and is owned by the container user (step 2).

**I declined the prompt by mistake.** Restart the watcher (`docker compose restart`) and accept it
this time.

## Settings

All optional except `TV_IP`. In Docker they go in `.env`; on the Pi in `/etc/omarchytv-homewatch.env`.

| Setting | Default | What it does |
|---|---|---|
| `TV_IP` | (required) | The TV's IP address or hostname. |
| `DATA_DIR` | `./data` | Docker only: host folder where the pairing key is kept. |
| `PUID` / `PGID` | `1000` | Docker only: user and group the container runs as; must be able to write `DATA_DIR`. |
| `TARGET_APP_ID` | `com.omarchytv.home` | App opened in place of LG Home. |
| `HOME_APP_IDS` | `com.webos.app.home,com.webos.launcher` | App ids treated as LG Home (comma-separated). |
| `SCREENSAVER_APP_IDS` | `com.webos.app.screensaver,com.webos.screensaver` | App ids treated as the screensaver. |
| `SSAP_URL` | automatic | Force one connection URL, e.g. `wss://192.168.1.50:3001`. |
| `STATE_FILE` | `/data/client-key.json` | Where the pairing key is saved (path as seen by the watcher). |

## Technical notes

- The watcher talks to the TV over LG's remote-control WebSocket (SSAP), the same one phone remote
  apps use. It tries the secure port (`wss://TV_IP:3001`, used by newer firmware) first, then the
  older `ws://TV_IP:3000`. The TV's certificate is self-signed, so the connection is encrypted but
  the certificate isn't verified.
- It asks for `READ_RUNNING_APPS`, `READ_POWER_STATE`, `CONTROL_POWER` and `LAUNCH`. Some firmware
  only reports power state to clients holding `CONTROL_POWER`; the watcher never sends a power
  command.
- This is separate from Developer Mode. It doesn't use the Key Server, the passphrase, port 9922 or
  `ares-cli`. Developer Mode still has to stay active for the OmarchyTV app itself.
- The Docker container publishes no ports; it only makes outgoing connections to the TV.

## Tests

The tests run the watcher against a fake TV (an in-process SSAP server) and cover redirecting on
Home, the debounce, leaving OmarchyTV alone, the screensaver and standby cases, and reconnecting:

```bash
pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

They can't check model-specific app ids or timing on real hardware; reports from different models
are welcome.

## References

- [webOS Homebrew command cheatsheet](https://www.webosbrew.org/pages/commands-cheatsheet): the SSAP foreground-app and power-state endpoints.
- [webos-vibehack](https://github.com/OmkarK97/webos-vibehack): earlier external Home redirect, and the `com.webos.app.home` id.
- [lgtv2](https://github.com/GermanBluefox/lgtv2): secure (`wss://:3001`) and legacy (`ws://:3000`) SSAP transports.
