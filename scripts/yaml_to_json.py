# -*- coding: utf-8 -*-
'''
scripts.yaml_to_json.py
Created on 09.05.2013
@author: tobixx0
'''
from __future__ import division, absolute_import, print_function
import json
import sys
import yaml

yaml_filename = sys.argv[1] 
json_filename = yaml_filename.split(".")[0] + ".json"

with open(yaml_filename) as f:
    y = list(yaml.load_all(f))

with open(json_filename, "w") as wf:
    json.dump(y, wf)