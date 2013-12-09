#/usr/bin/python3
#coding: utf8

"""
"""

import json
import re
import sys
from pprint import pprint

sys.path.append(".")

import piratetools42.logconfig
logg = piratetools42.logconfig.configure_logging()

WIKIARGUMENTS_BASE_URI = "http://bptarguments.piratenpartei.de/"

LINE_TMPL = "* {antrags_id}: [{base_uri}{antrags_id}/ {titel}]\n"


def create_line(antrag):
    line = LINE_TMPL.format(
            base_uri=WIKIARGUMENTS_BASE_URI,
            antrags_id=antrag["id"],
            titel=antrag["titel"])
    return line


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise Exception("mindestens 2 Argumente!!!")
    lines = []

    # in, create links
    with open(sys.argv[1]) as f:
        antraege = json.load(f)
        for antrag in antraege:
            line = create_line(antrag)
            lines.append(line)

    # out
    out_filename = sys.argv[2]
    if out_filename != "-":
        with open(out_filename, "w") as wf:
            wf.writelines(lines)
    else:
        pprint(lines)
