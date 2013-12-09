import sqlalchemy
import logging
from sqlalchemy import Table, MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.declarative import declarative_base

from piratetools42.localconfig import SQLALCHEMY_CONNECTION

logg = logging.getLogger(__name__)

logg.info("connection: %s", SQLALCHEMY_CONNECTION)
engine = create_engine(SQLALCHEMY_CONNECTION, echo=False)
metadata = MetaData()

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

questions = Table('questions', metadata, autoload=True, autoload_with=engine)
tags = Table('tags', metadata, autoload=True, autoload_with=engine)
localization = Table('localization', metadata, autoload=True, autoload_with=engine)


class Question(Base):
    __table__ = questions


class Tag(Base):
    __table__ = tags


class Localization(Base):
    __table__ = localization


def sqlsoup():
    import sqlsoup
    return sqlsoup.SQLSoup(SQLALCHEMY_CONNECTION)


# template for the strange additional data field from wikiarguments/questions
ADDITIONAL_DATA_TEMPLATE = 'O:8:"stdClass":4:{{s:7:"percPro";i:0;s:7:"percCon";i:0;s:11:"numCheckIns";i:0;s:4:"tags";a:{}:{{{}}}}}'


def create_additional_data(tags):
    tag_entries = []
    for num, tag in enumerate(tags):
        tag_entry = 'i:{};s:{}:"{}";'.format(num, len(bytes(tag, encoding="utf8")), tag.replace(" ", "-"))
        tag_entries.append(tag_entry)
    return ADDITIONAL_DATA_TEMPLATE.format(len(tags), "".join(tag_entries))


def test_additional_data():
    EXAMPLE_ADDITIONAL_DATA = 'O:8:"stdClass":4:{s:7:"percPro";i:0;s:7:"percCon";i:0;s:11:"numCheckIns";i:0;s:4:"tags";a:5:{i:0;s:1:"A";i:1;s:2:"BB";i:2;s:3:"CCC";i:3;s:4:"DDDD";i:4;s:4:"EEEE";}}'
    EXAMPLE_ADDITIONAL_DATA_2 = 'O:8:"stdClass":4:{s:7:"percPro";i:0;s:7:"percCon";i:0;s:11:"numCheckIns";i:0;s:4:"tags";a:1:{i:0;s:8:"Operbalz";}}'

    tags = ["A", "BB", "CCC", "DDDD", "EEEE"]
    tags2 = ["Opferbalz"]

    e2 = create_additional_data(tags2)
    assert e2 == EXAMPLE_ADDITIONAL_DATA_2

    e = create_additional_data(tags)
    assert e == EXAMPLE_ADDITIONAL_DATA


def truncate_tables(tables):
    for table in tables:
        session.execute("truncate " + table)
    session.commit()


def truncate_questions():
    tables = [
        "tags",
        "questions",
    ]
    truncate_tables(tables)


def truncate_votes():
    tables = [
        "user_factions",
        "user_votes",
    ]
    truncate_tables(tables)


def confirm_user():
    pass
