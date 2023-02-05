## Planewave EFA focuser daemon

`focusd` interfaces with and wraps a Hedrick Focuser / EFA and exposes it via Pyro.

`focus` is a commandline utility for controlling the focuser.

See [Software Infrastructure](https://github.com/warwick-one-metre/docs/wiki/Software-Infrastructure) for an overview of the software architecture and instructions for developing and deploying the code.

### Configuration

Configuration is read from json files that are installed by default to `/etc/focusd`.
A configuration file is specified when launching the server, and the `focus` frontend will search this location when launched.

The configuration options are:
```python
{
  "daemon": "localhost_test", # Run the server as this daemon. Daemon types are registered in `warwick.observatory.common.daemons`.
  "log_name": "focusd@test", # The name to use when writing messages to the observatory log.
  "control_machines": ["LocalHost"], # Machine names that are allowed to control (rather than just query) state. Machine names are registered in `warwick.observatory.common.IP`.
  "serial_port": "/dev/focuser", # Serial FIFO for communicating with the focuser
  "serial_baud": 19200, # Serial baud rate (always 19200)
  "serial_timeout": 5, # Serial comms timeout
  "idle_loop_delay": 5, # Delay in seconds between focuser status polls when idle
  "moving_loop_delay": 0.5, # Delay in seconds between focuser status polls when moving
  "move_timeout": 180 # Maximum time expected for a focus movement
}

```

## Initial Installation


The automated packaging scripts will push 4 RPM packages to the observatory package repository:

| Package                              | Description                                                                  |
|--------------------------------------|------------------------------------------------------------------------------|
| observatory-efafocus-server          | Contains the `focusd` server and systemd service file.                       |
| observatory-efafocus-client          | Contains the `focus` commandline utility for controlling the focuser server. |
| python3-warwick-observatory-efafocus | Contains the python module with shared code.                                 |
| halfmetre-efafocus-data              | Contains the json configuration for the half metre telescope.                |

`observatory-efafocus-server`, `observatory-efafocus-client` and `halfmetre-efafocus-data` should be installed on the `halfmetre-tcs` machine.

After installing packages, the systemd service should be enabled:

```
sudo systemctl enable focusd@<config>
sudo systemctl start focusd@<config>
```

where `config` is the name of the json file for the appropriate telescope.

Now open a port in the firewall:
```
sudo firewall-cmd --zone=public --add-port=<port>/tcp --permanent
sudo firewall-cmd --reload
```
where `port` is the port defined in `warwick.observatory.common.daemons` for the daemon specified in the config.

### Upgrading Installation

New RPM packages are automatically created and pushed to the package repository for each push to the `master` branch.
These can be upgraded locally using the standard system update procedure:
```
sudo yum clean expire-cache
sudo yum update
```

The daemon should then be restarted to use the newly installed code:
```
sudo systemctl stop focusd@<config>
sudo systemctl start focusd@<config>
```

### Testing Locally

The camera server and client can be run directly from a git clone:
```
./focusd test.json
FOCUSD_CONFIG_PATH=./test.json ./focus status
```
