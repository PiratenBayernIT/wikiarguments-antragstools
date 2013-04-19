#/usr/bin/python3
#coding: utf8

"""
"""

import json
import sys
import time
from pprint import pformat

sys.path.append(".")

import piratetools42.logconfig
logg = piratetools42.logconfig.configure_logging("prepare_bpt131.log")

WIKI_ANTRAGSBUCH_BASE_URI = "http://wiki.piratenpartei.de/Antrag:Bundesparteitag_2013.1/Antragsportal/"

def add_wiki_link(antrag):
    antrag["wiki"] = WIKI_ANTRAGSBUCH_BASE_URI + antrag["id"]


def filter_antrag(antrag):
    if antrag["prueficon"] != "2":
        return False
    return True

### config

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("keine Dateiname für das Antragsbuch angegeben!")
    antraege_filtered = []
    
    with open(sys.argv[1]) as f:
        antraege = json.load(f)
        for antrag in antraege:
            if filter_antrag(antrag):
                add_wiki_link(antrag)
                antraege_filtered.append(antrag)
            
    print(json.dumps(antraege_filtered))
    logg.info("Noch vorhandene Anträge %s, ausgefiltert: %s", len(antraege_filtered), len(antraege) - len(antraege_filtered))
            