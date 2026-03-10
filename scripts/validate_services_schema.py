#!/usr/bin/env python3
import json, yaml
from jsonschema import validate
schema = json.load(open('schemas/services.schema.json'))
data = yaml.safe_load(open('group_vars/all/main.yml')) or {}
validate(instance=data.get('services', {}), schema=schema)
print('services schema validation passed')
