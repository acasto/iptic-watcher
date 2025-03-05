# IPTIC Watcher

A lightweight, modular system monitoring tool that checks your servers and sends alerts if they go down.

## Features

- Lightweight and easy to deploy on any system
- Modular design for easy extension
- Currently supports ping and HTTP checks
- Email alerts via system mailer
- Simple configuration via INI format

## Installation

1. Clone the repository
2. Edit `config.ini` to add your systems
3. Make the main script executable: `chmod +x watcher.py`
4. Run the watcher: `./watcher.py`

## Usage

### Continuous Monitoring

```
./watcher.py
```

### Single-Shot Mode (for cron jobs)

```
./watcher.py --single-shot
```

Or more concisely:

```
./watcher.py -s
```

### Command Line Options

```
./watcher.py --help
```

- `--single-shot`, `-s`: Run once and exit (good for cron usage)
- `--config`, `-c`: Specify an alternative config file
- `--verbose`, `-v`: Show detailed output for all checks

## Configuration

Configuration is done via the `config.ini` file:

```ini
[systemname]
check = ping
host = example.com
alert = email

[webserver]
check = http
host = example.com
alert = email
```

### Available Check Types

- `ping`: Simple ping check (ICMP)
- `http`: HTTP/HTTPS check

### Available Alert Types

- `email`: System mail command

## Extending

### Adding New Check Types

1. Create a new Python file in the `checkers` directory (e.g., `checkers/tcp.py`)
2. Implement a `check(host, **kwargs)` function that returns `True` if successful, `False` otherwise
3. Use it in your config: `check = tcp`

### Adding New Alert Types

1. Create a new Python file in the `alerts` directory (e.g., `alerts/slack.py`)
2. Implement a `send_alert(system, host, message)` function
3. Use it in your config: `alert = slack`

## Running as a Service

### Systemd Service (Continuous Monitoring)

To run as a systemd service on Linux:

1. Create a service file in `/etc/systemd/system/iptic-watcher.service`:

```
[Unit]
Description=IPTIC Watcher Monitoring Service
After=network.target

[Service]
ExecStart=/path/to/iptic-watcher/watcher.py
WorkingDirectory=/path/to/iptic-watcher
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```
sudo systemctl enable iptic-watcher
sudo systemctl start iptic-watcher
```

### Cron Job (Single-Shot Mode)

Alternatively, you can use cron to run the watcher periodically in single-shot mode:

1. Open your crontab:

```
crontab -e
```

2. Add an entry to run the script every 5 minutes:

```
*/5 * * * * /path/to/iptic-watcher/watcher.py --single-shot
```

3. For email notifications to work with cron, ensure your system's mail configuration is working correctly.

The single-shot mode maintains state between runs by writing to a `.watcher_state` file, so it will still only alert on state changes, not on every run.

## License

MIT License