# Namecoin To Zonefile

This script generates a BIND zonefile from the Namecoin blockchain.

### Requirements
- Running instance of Namecoin
- jsonrpclib
..- `pip install jsonrpclib`

### Instructions
1. Clone this repository into `/opt/nmczone/` or a path of your choice
2. Install and configure Namecoin in `~/.namecoin/namecoin.conf`
3. Install and configure BIND
4. Populate `nmczone.conf` with the user and password from `~/.namecoin/namecoin.conf`
5. Add the authoritative nameserver and contact email in `nmczone.conf`
6. Run the script `update.sh` via cron at an interval of your choice.