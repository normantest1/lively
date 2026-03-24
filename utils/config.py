import json
import os
from pathlib import Path

ROOT_DIR = os.getcwd()

def deep_find(obj, target_attr):
    if hasattr(obj, target_attr):
        return getattr(obj, target_attr)

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == target_attr:
                return value
            result = deep_find(value, target_attr)
            if result is not None:
                return result

    elif isinstance(obj, (list, tuple)):
        for item in obj:
            result = deep_find(item, target_attr)
            if result is not None:
                return result

    return None

def load_config(path,field):
    with open(path,'r+',encoding="utf-8") as file:
        config = json.load(file)
    try:
        field = deep_find(config, field)
        return field
    except Exception as e:
        print(e)
        return None

