#!/bin/bash
cd /home/ian/url_diff
fin=0
while [ "$fin" -eq 0 ]
  do
    echo "Running"
    ./url_diff.py
    DAT=`date '+%d%m%Y-%H%M'`
#   tar cvzf saved/${DAT}.tar.gz snapshots/*.png >/dev/null 2>&1
    echo "Sleeping"
    sleep 15m
  done
