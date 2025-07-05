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

## Try it

```bash
$ pip install aetherterm
$ pip install aetherterm[themes]  # If you want to use themes
$ pip install aetherterm[systemd]  # If you want to use systemd
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

## APM Monitoring with Grafana Cloud

AetherTerm includes built-in OpenTelemetry instrumentation for comprehensive observability through Grafana Cloud APM.

### Features

- **Distributed Tracing**: Track requests across terminal sessions, WebSocket connections, and AI agent interactions
- **Custom Metrics**: Monitor terminal sessions, WebSocket traffic, AI token usage, and system resources
- **Structured Logging**: Correlated logs with trace IDs for debugging
- **Service Map**: Visualize dependencies and service interactions

### Setup

1. **Get Grafana Cloud Credentials**
   - Sign up for [Grafana Cloud](https://grafana.com/cloud/)
   - Create an API key with push permissions
   - Note your instance ID

2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Grafana Cloud credentials
   ```

3. **Required Environment Variables**
   ```bash
   GRAFANA_CLOUD_INSTANCE_ID="your-instance-id"
   GRAFANA_CLOUD_API_KEY="your-api-key"
   ENVIRONMENT="development"  # or staging, production
   ```

4. **Optional Configuration**
   ```bash
   OTEL_ENABLE_TRACING="true"
   OTEL_ENABLE_METRICS="true"
   OTEL_ENABLE_LOGGING="true"
   OTEL_TRACE_SAMPLE_RATE="1.0"
   ```

### Usage

Once configured, telemetry data will automatically be sent to Grafana Cloud:

```bash
# Start with APM enabled (default)
make run-agentserver

# Start with APM disabled
OTEL_ENABLE_TRACING=false make run-agentserver
```

### Available Metrics

- `aetherterm.terminal.sessions.active` - Active terminal sessions
- `aetherterm.websocket.connections.active` - Active WebSocket connections
- `aetherterm.ai.requests.total` - Total AI agent requests
- `aetherterm.ai.tokens.usage.total` - AI token consumption
- `aetherterm.system.memory.usage` - Memory usage
- `aetherterm.errors.total` - Error counts

### Grafana Dashboards

Pre-built dashboards are available for:
- Terminal session monitoring
- WebSocket connection health
- AI agent performance
- System resource utilization
- Error tracking and alerting

### Development

Enable console output for local development:

```bash
export OTEL_ENABLE_CONSOLE="true"
```

This will print telemetry data to the console in addition to sending to Grafana Cloud.
