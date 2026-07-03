# AstroForge — quick start

## 1. Install Docker Desktop (one-time only)

Download and install from: https://www.docker.com/products/docker-desktop/

Keep all default options during installation. When it's done, open Docker
Desktop and wait until the icon in the top bar (Mac) or bottom-right corner
(Windows) stops moving: that means it's ready.

## 2. Start AstroForge

In the `distribution` folder, double-click the file for your computer:

- **Windows** → `avvia.bat`
- **Mac** → `avvia.command`
- **Linux** → `avvia.sh`

A black window (the terminal) will open: that's normal, it shows what's
happening. The first time it takes a couple of minutes to download
everything; after that it's much faster.

Once everything is ready, the AstroForge dashboard will open directly in
that window.

## 3. Using the dashboard

Main keys:

| Key | What it does |
|---|---|
| `h` | Home |
| `a` | Asteroid list |
| `c` | Charts |
| `p` | Run analysis |
| `l` | Logs |
| `q` | Quit |

## 4. Shutting everything down

Press `q` in the dashboard: the window will automatically shut down all
the services. You can also just close the terminal window.

## Common issues

- **"Docker is not installed"**: go back to step 1.
- **The window closes immediately with an error**: make sure Docker
  Desktop is open and fully started before launching the script.
- **Everything is very slow the first time**: that's normal, it's
  downloading the images from the internet. You'll need a decent
  connection.
