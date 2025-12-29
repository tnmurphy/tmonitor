#!/usr/bin/env bash

(cd build && tar -czf - *) | ssh pi@chivero -C "cd /var/www/html/tmonitor && ls -l && sudo tar -xzf - && ls -l; sudo systemctl reload nginx"  

