#!/usr/bin/python

#
# V 0.4 - 25/3/17
# V 0.5 - 28/3/17
# V 0.6 - 30/3/17
# V 0.7 - 08/02/22

from ConfigParser import SafeConfigParser
from pprint import pprint
import ast
import re
import sys, os, subprocess, shutil
import time
import argparse
import datetime

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

config_parms = { 'proxy_server': '', 'proxy_username': '', 'proxy_password': '', 'proxy_type': 'http',
    'ssl_protocol': 'any', 'ignore_ssl_errors': 'True', 'extra_headers': [ ], 'user_agent': '', 'cookies_file': '',
    'screen_width': 1280, 'screen_height': 1024,
    'http_username': '', 'http_password': '', 'compare_fuzz': 0, 'diff_threshold': 0, 'diff_highlight': '', 'diff_lowlight': '',
    'thumbnail_width': 600, 'email_from': '', 'email_to': '', 'email_subject': '', 'attach_fullsize': True,
    'email_text': 'A %p% change has been detected in site %s (%u).\n\nThe current, previous, and difference images are attached.',
    'email_html': 'A <strong>%p%</strong> change has been detected in site <strong>%s</strong> (%u).<br /><br />Thumbnails of the current, previous, and difference images are shown below',
    'email_html_attach': ' - and the full images are attached.',
    'include_area': [], 'exclude_areas': [],
    'phantomjs_timeout': 30, 'phantomjs_bin': 'phantomjs', 'snapshot_dir': 'snapshots' ,
    'use_chrome': 'False', 'chrome_bin': 'chrome', 'frequency': 3600 ,
    'fail_on_match': 'False', 'fail_on_match_image': '', 'fail_on_match_area': [] }

#
# Log a status message
#

def log(log_ln):
    now_time = time.strftime("%d/%m/%Y %H:%M:%S")
    log_f = open(log_file, 'a')
    print "%s %s" % (now_time, log_ln)
    log_f.write("%s %s\n" % (now_time, log_ln))
    log_f.flush()
    os.fsync(log_f.fileno())

def run_status(stat_ln):
    now_time = time.strftime("%d/%m/%Y %H:%M:%S")
    print "%s %s" % (now_time, stat_ln)

#
# Log the execution of a command, a line of output from a command, or the return code of a command
#

def cmd_log(cmd, cmd_ln):
    log("Executing %s: %s" % (cmd, cmd_ln))
def cmd_log_out_ln(cmd, cmd_ln):
    log("%s: %s" % (cmd, cmd_ln))
def cmd_log_out(cmd, cmd_out):
    for cmd_ln in cmd_out.split("\n"):
        cmd_ln = cmd_ln.rstrip('\r\n')
        cmd_log_out_ln(cmd, cmd_ln)
def cmd_log_rc(cmd, cmd_rc):
    log("Return code %s from %s" % (cmd_rc, cmd))

#
# Abort
#

def abort(err_ln):
    print(err_ln)
    sys.exit(2)

#
# Abort with a config error
#

def config_error(parm, val, config_section, err_text):
    log("Error in configuration file '%s' section %s - the value '%s' for '%s' %s" % (config_file, config_section, val, parm, err_text))
    sys.exit(1)

#
# Parse a config file
#

def parse_config(config_file):
    global config
    global config_sections

    if not os.path.isfile(config_file):
       abort("Cannot open config file %s" % (config_file))

    config_parser = SafeConfigParser()
    config_parser.read(config_file)
    config_sections = config_parser.sections()
    for config_section in config_sections:
        config[config_section] = {}
        for (k, v) in config_parser.items(config_section):
            # print "k v type %s %s %s" % (k,v, type(v))
            if v.find('[') > -1:
                v = ast.literal_eval(v)
            elif len(v) > 0:
                if v[0] in [ '"', "'" ]:
                    v = v[1:]
                if v[-1] in [ '"', "'" ]:
                    v = v[:-1]
                v = v.strip()
                v = v.replace('\\', '%')
            config[config_section][k] = v

#
# Apply standard defaults just in case there is no 'defaults' section in the config file
#

def apply_config_defaults():
    if 'defaults' not in config:
        config['defaults'] = {}
    for (k, v) in config_parms.items():
        if k not in config['defaults']:
            config['defaults'][k] = v
# Apply defaults to all sections
    if 'defaults' in config.keys():
        for config_section in config_sections:
            if config_section == 'defaults':
                continue
            for key in config_parms:
                if key not in config[config_section].keys():
                    if key in config['defaults']:
                        config[config_section][key] = config['defaults'][key]

#
# Validate a config section
# This needs condensing so very much...

def validate_section(section):
    for parm in config_parms:
        val = config[section][parm]
        # Python, why do you not have a switch...
        if parm == 'proxy_server':
            pass
        elif parm == 'proxy_username':
            pass
        elif parm == 'proxy_password':
            pass
        elif parm == 'proxy_type':
            if val not in ['http', 'https']:
                config_error(parm, val, section, 'must be "http" or "https"')
        elif parm == 'ssl_protocol':
            if val not in ['SSLv3', 'SSLv2', 'TLSv1', 'any']:
                config_error(parm, val, section, 'must be "SSLvs", "SSLv2", "TLSv1" or "any"')
        elif parm == 'ignore_ssl_errors':
            if val in [ '1', 'True', 'true', 'TRUE' ]:
               config[section][parm] = True
            elif val in [ '0', 'False', 'false', 'FALSE' ]:
               config[section][parm] = False
            else:
               config_error(parm, val, section, 'must be "true" or "false"')
        elif parm == 'extra_headers':
            if type(val) is str:
                val = [ val ]
        elif parm == 'user_agent':
            pass
        elif parm == 'cookies_file':
            pass
        elif parm == 'screen_width':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'screen_height':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'http_username':
            pass
        elif parm == 'http_password':
            pass
        elif parm == 'compare_fuzz':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'diff_threshold':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'diff_highlight':
            pass
        elif parm == 'diff_lowlight':
            pass
        elif parm == 'thumbnail_width':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'email_from':
            if val == '':
                config_error(parm, val, section, 'must not be blank')
        elif parm == 'email_to':
            pass
        elif parm == 'email_subject':
            if val == '':
                config_error(parm, val, section, 'must not be blank')
        elif parm == 'include_area':
            if type(val) is str:
                val = [ val ]
            elif type(val) is not list:
                config_error(parm, val, section, 'must be a list with 4 elements')
            elif len(val) != 4:
                config_error(parm, val, section, 'must be a list with 4 elements')
        elif parm == 'exclude_areas':
            if type(val) is str:
                val = [ val ]
            elif type(val) is not list:
                config_error(parm, val, section, 'must be a list with 4 elements')
            elif (len(val) % 4) > 0:
                config_error(parm, val, section, 'must be a list with 4 elements per area')
        elif parm == 'attach_fullsize':
            if val in [ '1', 'True', 'true', 'TRUE' ]:
               config[section][parm] = True
            elif val in [ '0', 'False', 'false', 'FALSE' ]:
               config[section][parm] = False
            else:
               config_error(parm, val, section, 'must be "true" or "false"')
        elif parm == 'phantomjs_timeout':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'phantomjs_bin':
            config[section][parm] = val
        elif parm == 'use_chrome':
            if val in [ '1', 'True', 'true', 'TRUE' ]:
               config[section][parm] = True
            elif val in [ '0', 'False', 'false', 'FALSE' ]:
               config[section][parm] = False
            else:
               config_error(parm, val, section, 'must be "true" or "false"')
        elif parm == 'chrome_bin':
            config[section][parm] = val
        elif parm == 'frequency':
            if val.isdigit():
                config[section][parm] = int(val)
            else:
                config_error(parm, val, section, 'must be a positive integer')
        elif parm == 'fail_on_match':
            if val in [ '1', 'True', 'true', 'TRUE' ]:
               config[section][parm] = True
            elif val in [ '0', 'False', 'false', 'FALSE' ]:
               config[section][parm] = False
            else:
               config_error(parm, val, section, 'must be "true" or "false"')
        elif parm == 'fail_on_match_image':
            config[section][parm] = val
        elif parm == 'fail_on_match_area':
            if type(val) is str:
                val = [ val ]
            elif type(val) is not list:
                config_error(parm, val, section, 'must be a list with 4 elements')
            elif (len(val) % 4) > 0:
                config_error(parm, val, section, 'must be a list with 4 elements per area')


#
# Process a config section - this needs to be further split out into. Grab screenshot, process inc/exc, compare, extract, email
#

def run_section(section):
    if config[section]['url'] == '':
        log("Ignoring section %s as it has no url defined" % (section))
        return

# Ensure that snapshot directory exists
    if not os.path.exists(config[section]['snapshot_dir']):
        try:
            os.makedirs(config[section]['snapshot_dir'])
        except:
            log("Ignoring section %s as the snapshot directory %s cannot be created" % (section, config[section]['snapshot_dir']))
            return

# There was a previous successful run 
    last_success_file = config[section]['snapshot_dir'] + '/' + section + '-lastsuccess.txt'
    if os.path.exists(last_success_file):
        last_run_timestamp = os.stat(last_success_file).st_mtime
        last_run_datetime = datetime.datetime.fromtimestamp(last_run_timestamp)
        current_datetime = datetime.datetime.now()
        time_difference = current_datetime - last_run_datetime
        time_difference_secs = int(time_difference.total_seconds())

# Check that the last successful run isn't early, ie below the defined section's run frequency
        if time_difference_secs < config[section]['frequency']:
            log("Not processing section %s as it was processed %s seconds ago which is below the defined frequency of %s seconds" % (section, time_difference_secs, config[section]['frequency']))
            return

    log("Processing section %s" % (section))

# Note that we are attempting a run
    run_file = config[section]['snapshot_dir'] + '/' + section + '-lastrun.txt'
    with open(run_file, 'w') as f:
        f.write(' ')
 
# Grab the page
    if (config[section]['use_chrome']):
#./chrome --headless --window-size=1280,9000 --screenshot="/tmp/blah.png" 'https://dice.fm/search?query=rough%20trade%20east'
        cmd = "timeout " + str(config[section]['phantomjs_timeout']) +"s " + str(config[section]['chrome_bin'])
        cmd = cmd + " --headless --window-size=" + str(config[section]['screen_width']) + ',' + str(config[section]['screen_height']) + ' '
        cmd = cmd + " --screenshot='" + config[section]['snapshot_dir'] + "/output.png' "
        cmd = cmd + "'" + config[section]['url'] + "'"

        cmd_log("chrome", cmd)
    else:
        cmd = "timeout " + str(config[section]['phantomjs_timeout']) +"s " + str(config[section]['phantomjs_bin']) + " "
        if config[section]['ssl_protocol'] != '':
            cmd = cmd + '--ssl-protocol=' + config[section]['ssl_protocol'] + ' '
        if config[section]['proxy_server'] != '':
            cmd = cmd + '--proxy=' + config[section]['proxy_server'] + ' '
        if config[section]['proxy_username'] != '' and config[section]['proxy_password'] != '':
            cmd = cmd + '--proxy-auth=' + config[section]['proxy_username'] + ':' + config[section]['proxy_password'] + ' '
        if config[section]['ignore_ssl_errors']:
            cmd = cmd + '--ignore-ssl-errors=true '
        if config[section]['cookies_file'] != '':
            cmd = cmd + '--cookies-file=' + config[section]['cookies_file'] + ' '
        cmd = cmd + 'screenshot.js '
        cmd = cmd + "'" + config[section]['url'] + "' "
        cmd = cmd + config[section]['snapshot_dir'] + '/output.png '
        cmd = cmd + str(config[section]['screen_width']) + ' '
        cmd = cmd + str(config[section]['screen_height']) + ' '
        cmd = cmd + "'" + config[section]['user_agent'] + "' "
        cmd = cmd + "'" + config[section]['http_username'] + "' "
        cmd = cmd + "'" + config[section]['http_password'] + "' "
        cmd = cmd + "'" + ','.join(config[section]['extra_headers']) + "'"

        cmd_log("phantomjs", cmd)

    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cmd_out = proc.communicate()[0]
    cmd_rc = proc.returncode
    if config[section]['use_chrome']:
        cmd_log_rc("chrome", cmd_rc)
        cmd_log_out("chrome", cmd_out)
    else:
        cmd_log_rc("phantomjs", cmd_rc)
        cmd_log_out("phantomjs", cmd_out)

    if cmd_rc != 0:
        log("Ignoring section %s non-zero return code of %s from browser" % (section, cmd_rc))
        return

# Massive hack for dice failures. Sometimes the browser seems to signal page-load complete and exit before 
# the actual search contents have been rendered asynchronously. So this checks for a 700x700 black square
# in the search results - indicating that this has happened and that the run should be ignored and classed
# as a failure
    if config[section]['fail_on_match']:
        tmp_match = "/tmp/square.png"
        match_file = config[section]['fail_on_match_image']
        match_area = config[section]['fail_on_match_area']
#       cmd = "convert snapshots/"+section+".png -crop 700x700+100+300 "+tmp_match
        cmd = "convert "+config[section]['snapshot_dir']+"/output.png -crop "+str(match_area[2])+'x'+str(match_area[3])+'+'+str(match_area[0])+'+'+str(match_area[1])+" "+tmp_match
        cmd_log("fail_on_match convert", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        size_square = os.path.getsize(tmp_match)
        size_match = os.path.getsize(match_file)
        log("* fail_on_match compare size square %s match %s *" % (size_square, size_match))
        if size_square == size_match:
           log("fail_on_match conditions met, search render failed. Aborting this run")
           return

    if os.path.isfile(config[section]['snapshot_dir']+'/'+section + '.png'):
        log("Renaming %s/%s.png %s/%s-previous.png" % (config[section]['snapshot_dir'], section, config[section]['snapshot_dir'], section))
        os.rename(config[section]['snapshot_dir']+'/'+section + '.png', config[section]['snapshot_dir']+'/'+section + '-previous.png')

    log("Renaming %s/output.png %s/%s.png" % (config[section]['snapshot_dir'], config[section]['snapshot_dir'], section))
    os.rename(config[section]['snapshot_dir']+'/output.png', config[section]['snapshot_dir']+'/'+section + '.png')

    if not os.path.isfile(config[section]['snapshot_dir'] + '/' + section + '-previous.png'):
        log("This is the first run for this section, so not doing comparison")
        return

# Do include/exclude processing
    if len(config[section]['include_area']) != 0:
        # Include area
        i = config[section]['include_area']
        cmd = "convert %s/%s.png -crop %sx%s+%s+%s %s/%s-compare.png" % (config[section]['snapshot_dir'], section, i[0], i[1], i[2], i[3], config[section]['snapshot_dir'], section)
        cmd_log("convert", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        cmd_log_rc("convert", cmd_rc)
        cmd_log_out("convert", cmd_out)
        time.sleep(3)
        cmd = "convert %s/%s-previous.png -crop %sx%s+%s+%s %s/%s-previous-compare.png" % (config[section]['snapshot_dir'], section, i[0], i[1], i[2], i[3], config[section]['snapshot_dir'], section)
        cmd_log("convert", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        cmd_log_rc("convert", cmd_rc)
        cmd_log_out("convert", cmd_out)
        time.sleep(3)
    elif (len(config[section]['exclude_areas']) != 0):
        # Exclude areas
        i = config[section]['exclude_areas']
        draws = ''
        fill_colour = 'black'
        for n in range(0, len(i) // 4):
           p = (n * 4)
           draws = draws + '-draw "rectangle %s,%s %s,%s" ' % (i[p], i[p+1], i[p+2], i[p+3])
        cmd = "convert %s/%s.png -fill %s %s %s/%s-compare.png" % (config[section]['snapshot_dir'], section, fill_colour, draws, config[section]['snapshot_dir'], section)
        cmd_log("convert", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        cmd_log_rc("convert", cmd_rc)
        cmd_log_out("convert", cmd_out)
        time.sleep(3)
        cmd = "convert %s/%s-previous.png -fill %s %s %s/%s-previous-compare.png" % (config[section]['snapshot_dir'], section, fill_colour, draws, config[section]['snapshot_dir'], section)
        cmd_log("convert", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        cmd_log_rc("convert", cmd_rc)
        cmd_log_out("convert", cmd_out)
        time.sleep(3)
    else:
        # Just make a copy
        cmd_log("cp", 'cp '+config[section]['snapshot_dir']+'/'+section+'-previous.png '+config[section]['snapshot_dir']+'/'+section+'-previous-compare.png')
        shutil.copyfile(config[section]['snapshot_dir']+'/'+section+'-previous.png', config[section]['snapshot_dir']+'/'+section+'-previous-compare.png')
        cmd_log("cp", 'cp '+config[section]['snapshot_dir']+'/'+section+'.png '+ config[section]['snapshot_dir']+'/'+section+'-compare.png')
        shutil.copyfile(config[section]['snapshot_dir']+'/'+section+'.png', config[section]['snapshot_dir']+'/'+section+'-compare.png')

# Compare with previous
    if os.path.isfile(config[section]['snapshot_dir']+'/'+section + '-previous.png'):
        cmd = "compare -verbose -metric AE " 
        if (config[section]['compare_fuzz'] != '0'):
            cmd = cmd + "-fuzz '" + str(config[section]['compare_fuzz']) + "%' "
        if (config[section]['diff_highlight'] != ''):
            cmd = cmd + "-highlight-color '" + config[section]['diff_highlight'] + "' "
        if (config[section]['diff_lowlight'] != ''):
            cmd = cmd + "-lowlight-color '" + config[section]['diff_lowlight'] + "' "

        cmd = cmd + "%s/%s-compare.png %s/%s-previous-compare.png %s/%s-delta.png" % (config[section]['snapshot_dir'], section, config[section]['snapshot_dir'], section, config[section]['snapshot_dir'], section)
        cmd_log("compare", cmd)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd_out = proc.communicate()[0]
        cmd_rc = proc.returncode
        cmd_log_rc("compare", cmd_rc)
        percentage_difference = -1
        pixel_difference = -1
        curr_w = -1
        curr_h = -1 
        prev_w = -1
        prev_h = -1
        for cmd_ln in cmd_out.split("\n"):
            cmd_ln = cmd_ln.rstrip('\r\n')
            cmd_log_out_ln("compare", cmd_ln)
#           if cmd_ln.isdigit():
#               percentage_difference = cmd_ln
#bbc.png PNG 1280x3000 1280x3000+0+0 8-bit DirectClass 1.963MB 0.110u 0:00.120
            match = re.search(section+'-compare\.png PNG ([0-9]*)x([0-9]*) ', cmd_ln)
            if match:
                curr_w = int(match.group(1))
                curr_h = int(match.group(2))
            match = re.search(section+'-previous-compare\.png PNG ([0-9]*)x([0-9]*) ', cmd_ln)
            if match:
                prev_w = int(match.group(1))
                prev_h = int(match.group(2))
# all: 967
            match = re.search('all: ([0-9]*)', cmd_ln)
            if match:
                pixel_difference = int(match.group(1))
        if (curr_w == -1):
            abort("Can't extract current width")
        if (curr_h == -1):
            abort("Can't extract current height")
        if (prev_w == -1):
            abort("Can't extract previous width")
        if (prev_h == -1):
            abort("Can't extract previous height")
        if (pixel_difference == -1):
            abort("Can't extract pixel difference")
        if pixel_difference == 0:
            percentage_difference = 0
        else:
            percentage_difference = (float(pixel_difference) / float(curr_w * curr_h)) * 100.0
            percentage_difference = int(round(percentage_difference))
        log("Current image = %s x %s, previous image = %s x %s" % (curr_w, curr_h, prev_w, prev_h))
        log("Pixel/Percentage difference: %s %s" % (pixel_difference, percentage_difference))

# Note that we completed a run
        run_file = config[section]['snapshot_dir'] + '/' + section + '-lastsuccess.txt'
        with open(run_file, 'w') as f:  
            f.write(' ')

# Email differences
        if percentage_difference > int(config[section]['diff_threshold']):
            log("Thumbnailing")
            cmd = "convert %s/%s.png -resize %s %s/%s-thumbnail.png" % (config[section]['snapshot_dir'], section, config[section]['thumbnail_width'], config[section]['snapshot_dir'], section)
            cmd_log("convert", cmd)
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd_out = proc.communicate()[0]
            cmd_rc = proc.returncode 
            cmd_log_rc("convert", cmd_rc)
            cmd_log_out("convert", cmd_out)
            time.sleep(3)
            cmd = "convert %s/%s-previous.png -resize %s %s/%s-previous-thumbnail.png" % (config[section]['snapshot_dir'], section, config[section]['thumbnail_width'], config[section]['snapshot_dir'], section)
            cmd_log("convert", cmd)
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd_out = proc.communicate()[0]
            cmd_rc = proc.returncode
            cmd_log_rc("convert", cmd_rc)
            cmd_log_out("convert", cmd_out)
            time.sleep(3)
            cmd = "convert %s/%s-delta.png -resize %s %s/%s-delta-thumbnail.png" % (config[section]['snapshot_dir'], section, config[section]['thumbnail_width'], config[section]['snapshot_dir'], section)
            cmd_log("convert", cmd)
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd_out = proc.communicate()[0]
            cmd_rc = proc.returncode
            cmd_log_rc("convert", cmd_rc)
            cmd_log_out("convert", cmd_out)
            time.sleep(3)

            if config[section]['email_to'] == '':
                log("Not emailing differences email_to is blank")
                return

            log("Emailing differences")

            curr_time = time.strftime("%d/%m/%Y %H:%M:%S")

            mail_to = config[section]['email_from']
            mail_from = config[section]['email_to']
            mail_subject = config[section]['email_subject']

            mail_subject = mail_subject.replace('%s', section)
            mail_subject = mail_subject.replace('%u', config[section]['url'])
            mail_subject = mail_subject.replace('%p', str(percentage_difference))
            mail_subject = mail_subject.replace('%d', curr_time)

# Create the container (outer) email message.
            msg = MIMEMultipart()
            msg['Subject'] = mail_subject
            msg['From'] = mail_from
            msg['To'] = mail_to

            msg.preamble = 'This is a multi-part message in MIME format.\n'
            msg.epilogue = ''

            text = "A %p% change has been detected in site %s (%u) on %d.\n\nThe difference, current and previous images are attached."
            html = 'A <strong>%p%</strong> change has been detected in site <strong>%s</strong> (<a href="%u">%u</a>) on %d.<br /><br />Thumbnails of the current, previous, and difference images are shown below.'
            if (config[section]['attach_fullsize']):
                html = html + " - and the full images are attached."
            html = html + "<br /><br /><strong>Difference</strong><br /><img src=\"cid:imgdelta\"><br /><strong>Current image</strong><br /><img src=\"cid:imgcurr\"><br /><br /><strong>Previous image</strong><br /><img src=\"cid:imgprev\"><br /><br />"
            html = html + '<br /><br />'

            text = text.replace('%s', section)
            text = text.replace('%u', config[section]['url'])
            text = text.replace('%p', str(percentage_difference))
            text = text.replace('%d', curr_time)
            html = html.replace('%s', section)
            html = html.replace('%u', config[section]['url'])
            html = html.replace('%p', str(percentage_difference))
            html = html.replace('%d', curr_time)
            
            body = MIMEMultipart('alternative')
            body_text = MIMEText(text, 'plain')
            body_html = MIMEText(html, 'html')
            body.attach(body_text)
            body.attach(body_html)

            msg.attach(body)

            for (name, file) in { 'imgdelta': section+'-delta-thumbnail.png', 'imgcurr': section+'-thumbnail.png', 'imgprev': section+'-previous-thumbnail.png' }.items():
                fp = open(config[section]['snapshot_dir'] + '/' + file, 'rb')
                msgImage = MIMEImage(fp.read())
                fp.close()
                # Define the image's ID as referenced above
                msg.add_header('Content-ID', '<'+name+'>')
                msgImage['Content-ID'] = '<' + name + '>'
                msgImage['Content-Disposition'] = 'filename="%s"' % (file)
                msg.attach(msgImage)

            if (config[section]['attach_fullsize']):
                for file in [ section+'-delta.png', section+'.png', section+'-previous.png' ]:
                    with open(config[section]['snapshot_dir'] + '/' + file, 'rb') as fp:
                        img = MIMEImage(fp.read())
                    img['Content-Disposition'] = 'attachment; filename="%s"' % (file)
                    msg.attach(img)

# Send the email via our own SMTP server.
            s = smtplib.SMTP('localhost')
            s.sendmail(mail_from, mail_to, msg.as_string())
            s.quit()

# Note that we detected a change
            run_file = config[section]['snapshot_dir'] + '/' + section + '-lastchange,txt'
            with open(run_file, 'w') as f:  
                f.write(' ')

            return None

#
# Start
#

config_file = 'url_diff.ini'
log_file = 'url_diff.log'
verbose_option = False
debug_option = 0
parser = argparse.ArgumentParser()
parser.add_argument('--verbose', '-v', action='store_true', help='Verbose flag')
parser.add_argument('--config', '-c', type=str, help='Config file')
parser.add_argument('--log', '-l', type=str, help='Log file')
parser.add_argument('--debug', '-d', type=int, help='Debug level')
args = parser.parse_args()

if args.config:
    config_file = args.config
if args.log:
    log_file = args.log

run_status("Executing with config file %s and logging to %s" % (config_file, log_file))

config = {}

# Parse configuration
parse_config(config_file)

# Apply defaults
apply_config_defaults()

# Validate each config file section
for section in config_sections:
    validate_section(section)

# Process each config file section
for section in config_sections:
    if section != 'defaults':
        run_section(section)

sys.exit(0)

# End

