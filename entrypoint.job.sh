#!/bin/sh
# Export all environment variables to /etc/environment so cron can see them
printenv | grep -v "no_proxy" >> /etc/environment

# Start cron in foreground
cron -f
