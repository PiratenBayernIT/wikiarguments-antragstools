#/usr/bin/python3
#coding: utf8

"""Read JSON antrag files ("Antragsbücher") and write content to the wikiarguments DB"""

import difflib
import json
import sys
import re
from datetime import date
import time
from pprint import pformat

sys.path.append(".")

import piratetools42.logconfig
logg = piratetools42.logconfig.configure_logging("wikiarguments-import.log")
from piratetools42.wikiargumentsdb import create_additional_data, session, Question, Tag, truncate_database

### config

WIKI_BASE_URI = "http://wiki.piratenpartei.de/"
WIKIARGUMENTS_BASE_URI = "https://vdr:3000/141/"
#WIKIARGUMENTS_BASE_URI = "http://bptarguments.piratenpartei.de/141/"

HTML_ANTRAGS_TMPL = """\
{fulltitle_html}
<h2>Wiki</h2>
<a href="{info_url}">{info_url}</a>
<h2>Liquid Feedback</h2>
<a href="{lqfb_url}">{lqfb_url}</a>
<h2>Antragsteller</h2>
{owner}
<h2>Antragstext</h2>
{text}
<h2>Begründung</h2>
{motivation}
<h2>Eingetragen am / Letzte Aktualisierung</h2>
{changed}
"""

CODE_RE = re.compile('([A-Z"Ä]+)(\d\d\d\w?)')

BAD_ANTRAEGE_FIXES = {
# LPT BY 2012.2                      
# "PP092": lambda s: s.replace("\u2029", " ")
}

# special codes for the BPT.
CODE_TRANSLATION = {
}

# additional tags which are added to every antrag
ADDITIONAL_TAGS = ["BPT14.1"]

K = {
  "title": "titel",
  "owner": "autor",
  "motivation": "begruendung",
  "id": "id",
  "lqfb_url": "lqfb",
  "info_url": "wiki",
  "kind": "typ",
  "text": "text",
  "changed": "changed",
  "group": "gruppe"
}

# insert custom key mappings here if given JSON entries don't conform to the schema given in K

K.update({
})

# globals

# do we have a TO (Tagesordnung)?
TO_GIVEN = False


TODAY_DATE_STR = date.strftime(date.today(), "%d.%m.%Y")


antraege = {}
antrag_groups = {}


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
    title = a[K["id"]] + ": " + a[K["title"]]
    a[K["text"]] = a[K["text"]].rstrip("</p> </div> <p><br /> </p>")
    a.setdefault(K["lqfb_url"], "-")
    a.setdefault(K["motivation"], "-")
    a.setdefault(K["owner"], "-")
    a.setdefault(K["changed"], TODAY_DATE_STR)
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
    tags = [id_, a[K["kind"]], a[K["group"]]] + ADDITIONAL_TAGS
    if TO_GIVEN:
        # add TO position tags
        if to_pos != 0:
#             tags.append("Top80")
            tags.append("TO" + str(to_pos))
        else:
            tags.append("Rest")

    # insert question into DB
    additional = create_additional_data(tags)
    question = Question(title=a["shorttitle"], url=id_, details=details, dateAdded=time.time(),
                        score=0, scoreTrending=0, scoreTop=0, userId=2, groupId=0, type=0, flags=0, additionalData=additional)
    session.add(question)
    session.commit()
    # insert title words in Tag table because this table is used for question searches
    title_words = a[K["title"]].split()
    for tag in tags + title_words:
        tag_obj = Tag(tag=tag.replace(" ", "-"), questionId=question.questionId, groupId=0)
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
        if pretend:
            a = prepare_antrag(antrag)
            antrag_details_prepare_html(a)
        else:
            insert_antrag(antrag, to_pos)
        return "Neuer Antrag"

    # add to group overview
    group = antrag[K["group"]]
    grouplist = antrag_groups.setdefault(group, [])
    grouplist.append(id_)
    antraege[id_] = antrag


def read_TO(to_fn):
    """TO einlesen""" 
    with open(to_fn) as f:
        to_lines = f.readlines()
    to_order = [line.split(" ", 1)[0] for line in to_lines]
    return to_order


def create_group_overview():
    group_link_tmpl = '<a href="{}tags/title/{{}}/">{{}}</a>'.format(WIKIARGUMENTS_BASE_URI)
    antrag_li_tmpl = '<li><a href="{}{{0}}/">{{0}}: {{1}}</a></li>'.format(WIKIARGUMENTS_BASE_URI)
    content = ["<h2>Alle Antragsgruppen</h2>"]
    content.append("<ul>")
    content_all_antraege = ["<h2>Alle Anträge nach Gruppen</h2>"]
    content_all_antraege.append("<ul>")
    for group, members in sorted(antrag_groups.items()):
        group_formatted = group.replace(" ", "-")
        group_link = group_link_tmpl.format(group_formatted, group)
        content.append("<li>" + group_link + "</li>")
        content_all_antraege.append("<h3>" + group_link + "</h3>")
        content_all_antraege.append("<ul>")
        for antrag_id in sorted(members):
            title = antraege[antrag_id][K["title"]]
            content_all_antraege.append(antrag_li_tmpl.format(antrag_id, title))
        content_all_antraege.append("</ul>")
            

    content.append("</ul>")
    content += content_all_antraege
    return "\n".join(content)


def update_from_antragsbuch(antragsbuch_fn, to_fn, pretend):
    logg.info("---- Antragsbuch-Update gestartet ----")
    updated = {}
    failed = {}
    if TO_GIVEN:
        to_order = read_TO(to_fn)
        logg.debug("TO is %s", to_order)
    else:
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
#         logg.debug("code %s TO Pos is %s", code, to_pos)
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
        #overview = create_group_overview()
        logg.info("---- Antragsbuch-Update beendet ----")

    # show updated and failed antraege
    if updated:
        logg.debug("Geänderte Anträge:\n%s", pformat(updated))
    if failed:
        logg.warn("Es traten Fehler bei folgenden Anträgen auf:\n%s", pformat(failed))

    # show counts
    logg.info("Geänderte Anträge (Anzahl): %s", len(updated))
    if failed:
        logg.warn("Es traten Fehler bei Anträgen auf (Anzahl): %s", len(failed))
    return updated, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("keine Dateiname für das Antragsbuch angegeben!")
    # truncate
    if sys.argv[1] == "truncate":
        do_it = input("Wirklich alle Tags und Fragen löschen?!? (j/n) ")
        if do_it.lower() == "j":
            truncate_database()
            logg.info("alles gelöscht!")

        sys.exit(0)
    # update   
    do_it = input("Update durchführen? Bei nein wird nur angezeigt, was sich verändert hat und nichts an der DB geändert (j/n) ")
    pretend = False if do_it.lower() == "j" else True
    to_filename = sys.argv[2] if len(sys.argv) > 2 else None
    if to_filename:
        TO_GIVEN = True
    update_from_antragsbuch(sys.argv[1], to_filename, pretend)
    # write 
