AntragArguments
===============

Abhängigkeiten
--------------

* Python 3.x
* SQLAlchemy 0.8
* OurSQL3k 0.9.x


Debian-Install
--------------

Python:

    sudo apt-get install unzip python3 python3-dev python3-setuptools gcc
    sudo easy_install3 pip

OurSQL:

    wget https://launchpad.net/oursql/py3k/py3k-0.9.3/+download/oursql-0.9.3.zip
    unzip oursql-0.9.3.zip
    cd oursql-0.9.3
    sudo python3 setup.py install

SQLAlchemy:

    sudo pip install sqlalchemy


Datenbankeinstellungen
----------------------

* piratetools42/localconfig.py anlegen
* Beispiel unter piratetools42/localconfig.py.sample

Ausführbare Dateien
-------------------

* scripts/spickerrr.py - Führt ein Update der Wikiarguments-Datenbank durch


Beispiel
--------

* python3 scripts/spickerrr.py antraege/bylpt131-6647.json 
