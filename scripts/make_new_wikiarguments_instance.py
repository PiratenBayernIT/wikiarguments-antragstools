#!/usr/bin/env python3

import os
import os.path
import string
import sys
import subprocess

pjoin = os.path.join

### settings

INSTANCE = sys.argv[1]
LIGHTTPD_CONF_FILEPATH = "/dev/shm/lighttpd.conf"
LOG_PATH = "/dev/shm/"
ACCESS_LOG_PATH = pjoin(LOG_PATH, "access_{}.log".format(INSTANCE))
ERROR_LOG_PATH = pjoin(LOG_PATH, "error_{}.log".format(INSTANCE))
CONFIG_PATH = pjoin(INSTANCE, "etc/config.php")
DOMAIN = "piratenpartei-bayern.de"


def c(call):
    return subprocess.call(call, shell=True)


class Template(string.Template):
    delimiter = "#"


c("cp -lr wikiarguments_template {}".format(INSTANCE))
TEMPLATE = Template(open("wikiarguments_template/etc/config.php.template").read())
os.unlink(CONFIG_PATH)
with open(CONFIG_PATH, "w") as wf:
    wf.write(TEMPLATE.substitute(**vars()))


# lighttpd stuff

# create logfiles
c("touch " + ACCESS_LOG_PATH)
c("chown www-data:www-data " + ACCESS_LOG_PATH)
c("touch " + ERROR_LOG_PATH)
c("chown www-data:www-data " + ERROR_LOG_PATH)

LIGHTTPD_TEMPLATE = Template("""
$HTTP["host"] =~ "(^|\.)#{INSTANCE}.#{DOMAIN}" {
    server.document-root = var.basedir + "/#{INSTANCE}/"
    server.errorlog = "#{ERROR_LOG_PATH}"
    accesslog.filename = "#{ACCESS_LOG_PATH}"
}
""")

with open(LIGHTTPD_CONF_FILEPATH, "a") as wf:
    wf.write(LIGHTTPD_TEMPLATE.substitute(**vars()))
