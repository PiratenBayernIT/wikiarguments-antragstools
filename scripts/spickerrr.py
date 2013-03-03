#/usr/bin/python3
#coding: utf8

"""Read JSON antrag files ("Antragsbücher") from pirat.ly/spicker and write content to the wikiarguments DB
STATUS: works, some antraege need custom fixes for strange unicode chars (see BAD_ANTRAEGE_FIXES below)
"""

import difflib
import json
import sys
import re
import time
from pprint import pformat

sys.path.append(".")

import piratetools42.logconfig
logg = piratetools42.logconfig.configure_logging("wikiarguments-spickerrr-import.log")
from piratetools42.wikiargumentsdb import create_additional_data, session, Question, Tag, truncate_database

### config

WIKI_BASE_URI = "http://wiki.piratenpartei.de/"


HTML_ANTRAGS_TMPL = """\
{fulltitle_html}
<h2>Wiki</h2>
<a href="{info_url}">{info_url}</a>
<h2>Feedback</h2>
<a href="{lqfb_url}">{lqfb_url}</a>
<h2>Antragsteller</h2>
{owner}
<h2>Antragstext</h2>
{text}
<h2>Begründung</h2>
{motivation}
<h2>Letzte Änderung</h2>
{changed}
"""

CODE_RE = re.compile("(\w+)(\d\d\d)")

# we have to apply fixes for some 'antraege' when inserting into the DB
BAD_ANTRAEGE_FIXES = {
# "PP047": lambda s: s.replace("\u2191", "^"),
# "PP092": lambda s: s.replace("\u2029", " ")
}

# special codes for the LPT. Map BPT codes to LPT codes.
CODE_TRANSLATION = {
# "X": "SA",
# "P": "PP"
}

# additional tags which are added to every antrag
ADDITIONAL_TAGS = ["BPT12.2"]

K = {
  "title": "titel",
  "owner": "autor",
  "motivation": "begruendung",
  "id": "id",
  "lqfb_url": "lqfb", 
  "info_url": "wiki", 
  "kind": "typ",
  "text": "text",
  "changed": "changed"
}

# insert custom key mappings here if given JSON entries don't conform to the schema given in K

K.update({
  "title": "titel",
  "owner": "autor",
  "motivation": "begruendung",
  "lqfb_url": "lqfb", 
  "info_url": "wiki", 
  "kind": "typ",
})

def translate_antrags_code(antrag):
    """change antrag code and return fixed code"""
    code, number = CODE_RE.match(antrag[K["id"]]).groups()
    translated = CODE_TRANSLATION.get(code, code)
    id_ = translated + number
    antrag[K["id"]] = id_
    return id_


def antrag_details_prepare_html(a):
    html = HTML_ANTRAGS_TMPL.format(info_url=a[K["info_url"]], 
                                    lqfb_url=a[K["lqfb_url"]], 
                                    motivation=a[K["motivation"]], 
                                    text=a[K["text"]], 
                                    changed=a[K["changed"]], 
                                    owner=a[K["owner"]], 
                                    fulltitle_html=a["fulltitle_html"])
    fix = BAD_ANTRAEGE_FIXES.get(a[K["id"]])
    if fix:
        html = fix(html)
    return html


def prepare_antrag(antrag):
    a = antrag.copy()
    title = a[K["id"]] + ":" + a[K["title"]]
    a[K["text"]] = a[K["text"]].rstrip("</p> </div> <p><br /> </p>")
    a.setdefault(K["lqfb_url"], "-")
    a.setdefault(K["motivation"], "-")
    a.setdefault(K["owner"], "-")
    a.setdefault(K["changed"], "-")
    if len(title) > 100:
        logg.warn("%s: title too long: '%s'; shortened", a[K["id"]], title)
        # shorten title because wikiarguments supports only 100 chars
        # add full title to details
        a["fulltitle_html"] = "<h2>Voller Titel</h2>{}<br />".format(a[K["title"]])
        a["shorttitle"] = title[:97] + "..."
    else:
        a["fulltitle_html"] = ""
        a["shorttitle"] = title
        
    a[K["title"]] = title
    return a


def insert_antrag(antrag, to_pos):
    a = prepare_antrag(antrag)
    details = antrag_details_prepare_html(a)
    id_ = a[K["id"]]
    tags = [id_, a[K["kind"]]] + ADDITIONAL_TAGS
    # add TO position tags
    if to_pos != 0:
        tags.append("Top80")
        tags.append("TO" + str(to_pos))
    else:
        tags.append("Rest")
        
    # insert question into DB
    additional = create_additional_data(tags)
    question = Question(title=a["shorttitle"], url=id_, details=details, dateAdded=time.time(),
                        score=0, scoreTrending=0, scoreTop=0, userId=2, additionalData=additional)
    session.add(question)
    session.commit()
    # insert title words in Tag table because this table is used for question searches
    title_words = a[K["title"]].split()
    for tag in tags + title_words:
        tag_obj = Tag(tag=tag, questionId=question.questionId)
        session.add(tag_obj)
    session.commit()
    return question


def update_antrag(antrag, to_pos, pretend):
    id_ = antrag[K["id"]]
    question = session.query(Question).filter_by(url=id_).first()
    if question:
        logg.info("Antrag %s existiert schon", id_)
        # update details if changed. Other fields must not change and are ignored
        a = prepare_antrag(antrag)
        details = antrag_details_prepare_html(a)
        if question.details != details:
            diff = list(difflib.Differ().compare(question.details.split("\n"), details.split("\n")))
            logg.info("Antragsdetails von %s haben sich verändert, Unterschiede:\n %s", id_, pformat(diff))
            if not pretend:
                question.details = details
                session.commit()
            return diff
    else:
        logg.info("Antrag ist neu: '%s'", id_)
        if not pretend:
            insert_antrag(antrag, to_pos)
        return "Neuer Antrag"


def read_TO(to_fn):
    """TO einlesen""" 
    with open(to_fn) as f:
        to_lines = f.readlines()
    to_order = [line.split(" ", 1)[0] for line in to_lines]
    return to_order


def update_from_antragsbuch(antragsbuch_fn, to_fn, pretend):
    logg.info("---- Antragsbuch-Update gestartet ----")
    updated = {}
    failed = {}
#     to_order = read_TO(to_fn)
    to_order = []
    with open(antragsbuch_fn) as f:
        antragsbuch = json.load(f)
    for antrag in antragsbuch:
        code = translate_antrags_code(antrag)
        # find position in TO, 0 if not found
        try:
            to_pos = to_order.index(code) + 1
        except ValueError:
            to_pos = 0
        try:
            diff = update_antrag(antrag, to_pos, pretend)
        except Exception as e:
            logg.error("error inserting antrag '%s', error '%s'", antrag[K["id"]], e)
            failed[antrag[K["id"]]] = e
            session.rollback()
        else:
            if diff:
                updated[antrag[K["id"]]] = diff

    if pretend:
        logg.info("---- Nichts geändert, es werden nur die Unterschiede angezeigt ----")
    else:
        logg.info("---- Antragsbuch-Update beendet ----")
        
    if updated:
        logg.info("%s geänderte Anträge:\n%s", len(updated), pformat(updated))
    if failed:
        logg.warn("Es traten Fehler bei %s Anträgen auf:\n%s", len(failed), pformat(failed))
    return updated, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("keine Dateiname für das Antragsbuch angegeben!")
    do_it = input("Update durchführen? Bei nein wird nur angezeigt, was sich verändert hat und nichts an der DB geändert (j/n) ")
    pretend = False if do_it.lower() == "j" else True
    to_filename = sys.argv[2] if len(sys.argv) > 2 else None
    update_from_antragsbuch(sys.argv[1], to_filename, pretend)