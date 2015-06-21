#!/bin/sh
cd /opt/nmczone/
/usr/bin/python ./generate-zone.py
service bind9 reload
