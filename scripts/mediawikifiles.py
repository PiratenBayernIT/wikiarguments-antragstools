#/usr/bin/python3
#coding: utf8
"""
Parse .antrag files, convert to JSON and write content into the wikiarguments DB 
STATUS: mediawiki_parser incompatible with Python3, doesn't work for some files, wikiarguments inserting incomplete (see spickerrr.py)
"""

import json
import glob
import logging as logg
import codecs
import time
import re
import os.path
from piratetools42.wikiargumentsdb import create_additional_data

logg.basicConfig(level=logg.DEBUG)

# config

WIKI_BASE_URI = "http://wiki.piratenpartei.de/"


ANTRAGS_RE = re.compile("\
\|landesparteitag=(?P<lpt>.*?)\n*\
\|antragsart=(?P<antragsart>.*?)\n*\
\|titel=(?P<titel>.*?)\n*\
\|autor=(?P<autor>.*?)\n*\
\|text=(?P<text>.*?)\n*\
(?:\|begruendung=(?P<begruendung>.*?)\n*)?\
(?:\|ebene=(?P<ebene>.*?)\n*)?\
(?:\|vorher=(?P<vorher>.*?)\n*)?\
(?:\|nachher=(?P<nachher>.*?)\n*)?\
(?:\|pfb=(?P<pfb>.*?)\n*)?\
(?:\|podcast=(?P<podcast>.*?)\n*)?\
(?:\|pad=(?P<pad>.*?)\n*)?\
\|eingereicht=(?P<eingereicht>\d)\n*", flags=re.DOTALL | re.UNICODE)

ANTRAGSNAME_RE = re.compile("(.+)_(\d\d\d)\.antrag", flags=re.UNICODE)

TESTANTRAG = ("""\
|landesparteitag=2013.1
|antragsart=Positionspapier
|titel=Zeitreisen sind Kinderkacke
|autor=DNT
|text=BLA!
mehr Text
Multiline
Spam
|begruendung=SPAM!
|eingereicht=1
""")


HTML_ANTRAGS_TMPL = """\
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>
<h2>Wiki</h2>
<a href="{wiki}">{wiki}</a>
<h2>Pirate Feedback</h2>
<a href="{pfb}">{pfb}</a>
<h2>Antragstext</h2>
{text}
<h2>Begründung</h2>
{begruendung}
</body>
"""


ANTRAG_TYPES = {
    "Positionspapier": "PP",
    "Satzungsänderung": "SÄA",
    "Sonstiger_Antrag": "X",
    "Bundesprogramm": "BP"
}

ALL_TAGS = ["landesparteitag", "antragsart", "titel", "autor", "text", "begruendung", "vorher", "nachher", "ebene", "pfb", "pad", "eingereicht"]
ALL_TAGS_BAR = ["|" + t for t in ALL_TAGS]

ANTRAGS_FILENAME_GLOB = glob.glob("lpt131/*.antrag")


def match_antrags_file(filename):
    with codecs.open(filename, encoding="utf8") as f:
        text = f.read()
    match = ANTRAGS_RE.match(text)
    return match


def check_antrag_validity(filename):
    match = match_antrags_file(filename)
    if match:
        d = match.groupdict()
        fail = False
        for tag in ALL_TAGS_BAR:
            for v in d.values():
                if v and tag in v:
                    logg.warn("tag '%s' found in '%s'", tag, v)
                    fail = True
        if fail:
            return False
    else:
        logg.warn("'%s': no match!", filename)
        return False

    try:
        js = antrag_wikifile_to_json(filename)
    except Exception as e:
        logg.warn("'%s': error converting to JSON!", filename)
        logg.error("%s", e)
        return False
    try:
        html = antrag_json_to_html(js)
    except Exception as e:
        logg.warn("'%s': error converting to HTML!", filename)
        logg.error("%s", e)
        return False

    logg.info("'%s': ok", filename)
    return True


def check_all_antraege():
    failed = []
    for f in ANTRAGS_FILENAME_GLOB:
        ok = check_antrag_validity(f)
        if not ok:
            failed.append(f)
    return failed


def render_html(text):
    if not text.strip():
        return ""
    preprocessed_text = preprocessor.parse(text)
    output = postprocessor.parse(preprocessed_text.leaves())
    return output.value


def antrag_wikifile_to_json(filename):
    match = match_antrags_file(filename)
    if match:
        d = match.groupdict()
        d.update(dict((k, v.strip()) for k, v in d.iteritems() if v))
        antrag_typ, antrag_nummer = ANTRAGSNAME_RE.match(os.path.basename(filename)).groups()
        antrag_name = antrag_typ + "_" + antrag_nummer
        antrag_shortname = ANTRAG_TYPES[antrag_typ] + antrag_nummer
        d["wiki"] = "BY:Landesparteitag_2013.1/Antragsfabrik/{}".format(antrag_name)
        d["id"] = antrag_shortname
        return d


def antrag_json_to_html(antrag_json):
    text = render_html(antrag_json["text"]).lstrip("<body>").rstrip("</body>") or "-"
    begruendung = render_html(antrag_json["begruendung"]).lstrip("<body>").rstrip("</body>") or "-"
    pfb = antrag_json["pfb"] or "-"
    wiki = WIKI_BASE_URI + antrag_json["wiki"]
    autor = antrag_json["autor"]
    html = HTML_ANTRAGS_TMPL.format(**locals())
    return html


def make_parsers():
    templates = {}
    allowed_tags = []
    allowed_self_closing_tags = []
    allowed_attributes = []
    interwiki = {}
    namespaces = {}

    from mediawiki_parser.preprocessor import make_parser
    preprocessor = make_parser(templates)

    from mediawiki_parser.html import make_parser
    parser = make_parser(allowed_tags, allowed_self_closing_tags, allowed_attributes, interwiki, namespaces, internal_link_prefix=WIKI_BASE_URI)

    return preprocessor, parser


def insert_antrag_into_wikiarguments(filename):
    from wikiargumentsdb import session, Question, Tag
    js = antrag_wikifile_to_json(filename)
    details = antrag_json_to_html(js)
    id_ = js["id"]
    tags = [id_, "LPT13.1", js["antragsart"]]
    additional = create_additional_data(tags)
    title = id_ + ":" + js["titel"]
    question = Question(title=title, url=id_, details=details, dateAdded=time.time(), score=0, scoreTrending=0, scoreTop=0, userId=2, additionalData=additional)
    session.add(question)
    session.commit()
    for tag in tags:
        tag_obj = Tag(tag=tag, questionId=question.questionId)
        session.add(tag_obj)
    session.commit()
    return question


def insert_all():
    for filename in ANTRAGS_FILENAME_GLOB:
        try:
            insert_antrag_into_wikiarguments(filename)
        except:
            from wikiargumentsdb import session
            session.rollback()


if __name__ == "__main__":
    preprocessor, postprocessor = make_parsers()
