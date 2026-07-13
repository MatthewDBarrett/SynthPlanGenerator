# Deploying to a Raspberry Pi

These steps install the app as a `systemd` service on Raspberry Pi OS Lite (32-bit), running under [gunicorn](https://gunicorn.org/) so it survives reboots and restarts itself if it crashes. They work the same on any Debian-based Linux.

Run everything below **on the Pi itself** (over SSH is fine) — not from this dev machine.

## 1. Install git (if not already present)

```
$ sudo apt-get update
$ sudo apt-get install -y git
```

## 2. Clone the repo

```
$ git clone https://github.com/MatthewDBarrett/SynthPlanGenerator.git ~/family-tree
$ cd ~/family-tree
```

If this hasn't been merged to `main` yet, check out this branch instead:

```
$ git checkout claude/self-hosted-ancestry-site-g1cqmd
```

## 3. Run the installer

```
$ ./deploy/install.sh
```

Run it as your normal user — **not** with `sudo`. It installs `python3-venv`, creates a virtual environment, installs dependencies (using [piwheels](https://www.piwheels.org/) so Pillow doesn't need to compile from source), and installs + starts a `family-tree` systemd service.

It prints the URL to visit when it's done, something like `http://192.168.1.42:8080`.

To use a different port or worker count:

```
$ PORT=9000 WORKERS=1 ./deploy/install.sh
```

(1 worker is a reasonable choice if the Pi 3B ever feels sluggish — it has 1GB of RAM total.)

## Updating later

```
$ cd ~/family-tree
$ git pull
$ ./deploy/install.sh
```

The script is safe to re-run — it reuses the existing virtual environment, updates dependencies, and restarts the service.

## Managing the service

```
$ sudo systemctl status family-tree     # is it running?
$ sudo systemctl restart family-tree
$ sudo systemctl stop family-tree
$ sudo journalctl -u family-tree -f     # live logs
```

## Your data

The SQLite database and uploaded photos/documents live in `~/family-tree/instance/` (created automatically on first run). This directory is what you should back up — copy it somewhere else periodically, e.g.:

```
$ tar czf family-tree-backup-$(date +%F).tar.gz -C ~/family-tree instance
```

You can also export a GEDCOM file from the app itself (Import / Export page) as a portable backup.

## Accessing it from other devices

The app binds to `0.0.0.0`, so any device on your home network can reach it at `http://<pi-ip>:<port>`. Find the Pi's address with `hostname -I` on the Pi, or check your router's device list. Consider giving the Pi a static/reserved IP on your router so the address doesn't change.

There's no login/authentication yet, so anyone on your home network can view and edit the tree. **Don't port-forward this to the public internet** as-is. If you want to reach it from outside your home later, use something like [Tailscale](https://tailscale.com/) or [WireGuard](https://www.wireguard.com/) to put your devices on the same private network instead of exposing it directly.

## Troubleshooting

- **Pillow fails to install**: piwheels doesn't have a wheel for your exact Python version yet. Install build dependencies and retry: `sudo apt-get install -y build-essential libjpeg-dev zlib1g-dev libopenjp2-7 libtiff6 && ./deploy/install.sh` (this will compile Pillow from source, which is slow on a Pi 3B — expect several minutes).
- **Port already in use**: another service is using port 8080. Re-run with `PORT=8081 ./deploy/install.sh` (or any free port).
- **Service won't start**: check `sudo journalctl -u family-tree -e` for the actual error.
