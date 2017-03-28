
function csv2array(instr)
{
  var in_quote = 0;
  var in_backtick = 0;
  var out_arr = [];
  var curr = '';
  var n;
  for (n = 0; n < instr.length; n++)
    {
      if (instr[n] == '\\')
        {
          in_backtick = 1;
          continue;
        }
      if ((instr[n] === '"') && (in_quote) && (!in_backtick))
        {
          out_arr.push(curr);
          in_quote = 0;
          curr = '';
        }
      else if (instr[n] === '"' && (!in_backtick))
        {
          in_quote = 1;
         }
      else if ((instr[n] === ",") && (!in_quote))
        {
          out_arr.push(curr);
          curr = '';
        }
      else
        {
          curr = curr + instr[n];
        }
      in_backtick = 0;
    }
  if (curr != '')
    {
      out_arr.push(curr)+"X";
    }
  return out_arr;
}

var page = require('webpage').create(),
  system = require('system'),
  load_time, load_url, screen_w, screen_h, user_agent, http_user, http_pass, t;

if (system.args.length < 3) {
  console.log('Usage: screenshot.js <URL> <image_file> (<width>) (<height>) (<user_agent>) (<http_username>) (<http_password>)');
  phantom.exit();
}

load_url = system.args[1]
screen_file = system.args[2]

screen_w = 1280
screen_h = 1024
user_agent = ''
http_user = ''
http_pass = ''
extra_headers = ''

if (system.args.length > 3)
{
  if (system.args[3] != '')
    { screen_w = system.args[3] }
}
if (system.args.length > 4)
{
  if (system.args[4] != '')
    { screen_h = system.args[4] }
}
if (system.args.length > 5)
{
  if (system.args[5] != '')
    { user_agent = system.args[5] }
}
if (system.args.length > 6)
{
  if (system.args[6] != '')
    { http_user = system.args[6] }
}
if (system.args.length > 7)
{
  if (system.args[7] != '')
    { http_pass = system.args[7] }
}
if (system.args.length > 8)
{
  if (system.args[8] != '')
    { extra_headers = system.args[8] }
}

//viewportSize being the actual size of the headless browser
page.viewportSize = { width: screen_w, height: screen_h };
//the clipRect is the portion of the page you are taking a screenshot of
page.clipRect = { top: 0, left: 0, width: screen_w, height: screen_h };

t = Date.now()
console.log('Loading ' + load_url + ' (' + screen_w + 'x' + screen_h + ')');
if (user_agent != '')
{
 page.settings.userAgent = user_agent;
}
if (http_user != '')
{
 page.settings.userName = http_user;
}
if (http_pass != '')
{
 page.settings.password = http_pass;
}

if (extra_headers != '')
{
 var arr = csv2array(extra_headers);
 var hdrs = {}
 for (n = 0; n < arr.length; n++)
   {
     p = arr[n].indexOf(":");
     hdn = arr[n].substr(0, p);
     hdv = arr[n].substr(p + 1);
     hdrs[hdn] = hdv;
   } 
 page.customHeaders = hdrs;
}

page.open(load_url, function(status) {
  if (status !== 'success') {
    console.log('Failed to load ' + load_url);
    phantom.exit(1)
  } else {
    load_time = Date.now() - t;
    console.log('Loaded ' + load_url + ' in ' + load_time + ' mS');
    console.log('Saving as ' + screen_file);
    page.render(screen_file);
  }
  phantom.exit(0);
});

