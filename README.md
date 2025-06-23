# ⚡ AetherTerm

## Description

AetherTerm is a xterm compatible terminal that runs in your browser.

## Features

- xterm compatible (support a lot of unused features!)
- Native browser scroll and search
- Theming in css / sass - endless possibilities!
- HTML in your terminal! cat images and use <table>
- Multiple sessions support (à la screen -x) to simultaneously access a terminal from several places on the planet!
- Secure authentication with X509 certificates!
- 16,777,216 colors support!
- Keyboard text selection!
- Desktop notifications on terminal output!
- Geolocation from browser!
- **MOTD (Message of the Day)** - Customizable welcome message with connection info and branding!
- Cross-browser compatibility!

## Installation Options

AetherTerm offers flexible installation options based on your needs:

### Core Installation (Lightweight)
```bash
# Basic terminal functionality only (~50MB)
uv sync
# or
pip install aetherterm
```

### AI-Enhanced Installation (Recommended)
```bash
# Full AI chat and LangChain support (~500MB)
uv sync --extra ai
# or
pip install aetherterm[ai]
```

### Minimal AI Installation
```bash
# LangChain and AI providers only (~100MB)
uv sync --extra langchain
# or
pip install aetherterm[langchain]
```

### Complete Installation
```bash
# All features including ML/AI (~2GB)
uv sync --extra all
# or
pip install aetherterm[all]
```

### Development Installation
```bash
# For development with all tools
uv sync --extra dev
# or
pip install aetherterm[dev]
```

See [Optional Dependencies Guide](docs/OPTIONAL_DEPENDENCIES.md) for detailed information.

## Quick Start

```bash
$ aetherterm
```

A new tab should appear in your browser. Then type

```bash
$ aetherterm help
```

To get an overview of AetherTerm features.

## Run it as a server

```bash
$ aetherterm --host=myhost --port=57575
```

Or with login prompt

```bash
$ aetherterm --host=myhost --port=57575 --login
```

Or with PAM authentication (ROOT required)

```bash
# aetherterm --host=myhost --port=57575 --login --pam_profile=sshd
```

You can change `sshd` to your preferred PAM profile.

## Run it with systemd (linux)

Systemd provides a way to automatically activate daemons when needed (socket activation):

```bash
$ cd /etc/systemd/system
$ # Create service files for aetherterm
$ systemctl enable aetherterm.socket
$ systemctl start aetherterm.socket
```

Don't forget to update the /etc/aetherterm/aetherterm.conf file with your server options (host, port, shell, ...) and to install aetherterm with the [systemd] flag.

## Contribute

and make the world better (or just AetherTerm).

Don't hesitate to fork the repository and start hacking on it, I am very open to pull requests.

If you don't know what to do go to the github issues and pick one you like.

Client side development use modern web technologies.

## Credits

The js part is based on [term.js](https://github.com/chjj/term.js/) which is based on [jslinux](http://bellard.org/jslinux/).

## Author

[Florian Mounier](http://paradoxxxzero.github.io/)

## License

```
Copyright 2025

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Docker

### Example usage

Starting with login and password

```bash
docker run --env PASSWORD=password -d aetherterm/aetherterm --login
```

Starting with no password

```bash
docker run -d -p 57575:57575 aetherterm/aetherterm
```

Starting with a different port

```bash
docker run -d -p 12345:12345 aetherterm/aetherterm --port=12345
```
