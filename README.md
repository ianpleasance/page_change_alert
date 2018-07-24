# page_change_alert
Tool to monitor a set of web pages and alert when they change visually



Purpose

This script monitors a series of URLs and alerts on visual change to them. It was designed to monitor sites that don't have easily parsable HTML, which don't have RSS feeds, or which have non HTML components such as Java or heavy DHTML'd sites.

It takes a snapshot of the URL (via phantomjs), optionally includes or excludes areas that regularly change, compares (with imagemagick) the snapshot with the previously retrieved version and then if the delta between the current and previous images exceeds a percentage threshold then it emails an alert containing a small version of the current, previous, and overlay difference images.

For optimal use it needs to be run via cron or as a service

---------------------------------

To do

- Tidy, refactor

- Some of the regexing of command outputs could do with being hardened

- Libraryize core routines

- Implement verbose and debug parameter options

- If you change the screenshot size then the comparison with the previous one fails - need to read the size of the previous one and skip the comparison if the sizes are different to the new one

- If phantomjs fails and never exits then the script dies, need to put a timer around the fork/exec calls
  = Also change settings.resourceTimeout to change the phantomjs resource load timeout, resourceTimeout (in milli-secs) 

- If you dont specify a parameter in the default section then there are some validation errors. e.g. remove phantomjs_timeout from defaults in the ini and it will fail

- Write installation docs

- Needs a front-end so that URLs can be added and include/exclude areas selected via a UI without having to work out the coordinates manually

- Needs a cronjob written, or an /etc/init.d/ launcher/runscript and wrappers to make it a service

- Document the zabbix alerts that I've done for it not running

------

Installation

on Ubuntu

sudo apt-get install phantomjs imagemagick
sudo pip install ast

-------

Random notes

phantomjs --ssl-protocol=any
 (Doesnt complain about self-signed/mid-chain certificates)

phantomjs --ssl-protocol=any screenshot.js http://news.bbc.co.uk/ bbc.png 1280 6000

--cookies-file=<file> - Save cookies in a file for persistence
--ignore-ssl=errors=true - Ignore SSL errors for self-signed certs
--proxy=http://myproxy.com:8080
--proxy-auth=username:password
--proxy-type=http
--ssl-protocol=<val> - val is 'SSLv2', 'TLSv1', 'any'

This jquery plugin looks useful for area selection

https://github.com/360Learning/jquery-select-areas.git
