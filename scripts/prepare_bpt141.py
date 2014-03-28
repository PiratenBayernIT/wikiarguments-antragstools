#/usr/bin/python3
#coding: utf8

"""
"""

import json
import re
import sys

sys.path.append(".")

import piratetools42.logconfig
logg = piratetools42.logconfig.configure_logging("prepare_bpt141.log")

WIKI_ANTRAGSBUCH_BASE_URI = "http://wiki.piratenpartei.de/Antrag:Bundesparteitag_2014.1/Antragsportal/"

TEX_LABEL_RE = re.compile("\\\\label{.+?}")
HTML_TAG_RE = re.compile("<br>")
TEX_HYPER_RE = re.compile("\\\\hyperref\[.+?\]{.+?}")
CODE_RE = re.compile('([A-Z"Ä]+)(\d\d\d)')

ANTRAEGE_TO_REMOVE = [
"S\"AA013",
"GP005",
"GP010",
"GP011",
"WP017",
"WP020",
"WP028",
"WP029",
"WP048",
"WP050",
"WP054",
"WP056",
"WP057",
]


def change_saa(antrag):
    code, number = CODE_RE.match(antrag["id"]).groups()
    if code == "S\"AA":
        antrag["id"] = "SÄA" + number


def add_wiki_link(antrag):
    antrag["wiki"] = WIKI_ANTRAGSBUCH_BASE_URI + antrag["id"]


def remove_tex_label(antrag):
    antrag["text"] = TEX_LABEL_RE.sub("", antrag["text"])
    antrag["begruendung"] = TEX_LABEL_RE.sub("", antrag["begruendung"])
    antrag["text"] = TEX_HYPER_RE.sub("", antrag["text"])
    antrag["begruendung"] = TEX_HYPER_RE.sub("", antrag["begruendung"])


def remove_html_tags(antrag):
    antrag["titel"] = HTML_TAG_RE.sub(" - ", antrag["titel"])


def filter_antrag(antrag):
    if antrag["id"] in ANTRAEGE_TO_REMOVE:
        return False
    return True


### config

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise Exception("mindestens 2 Argumente!!!")
    antraege_filtered = []

    with open(sys.argv[1]) as f:
        antraege = json.load(f)
        for antrag in antraege:
            if filter_antrag(antrag):
                change_saa(antrag)
                add_wiki_link(antrag)
                remove_html_tags(antrag)
                antraege_filtered.append(antrag)
    out_filename = sys.argv[2]

    if out_filename != "-":
        with open(out_filename, "w") as wf:
            json.dump(antraege_filtered, wf, indent=2)
    else:
        print(json.dumps(antraege_filtered, indent=2))

    logg.info("Noch vorhandene Anträge %s, ausgefiltert: %s", len(antraege_filtered), len(antraege) - len(antraege_filtered))
    logg.info("Ausgefilterte Anträge: %s", set(a["id"] for a in antraege) ^ set(a["id"] for a in antraege_filtered))

