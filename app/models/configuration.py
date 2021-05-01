from models.constants import CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME
from os import path
import json

try:
    config = path.join(CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME)
    with open(config) as configuration_file:
        config = json.load(configuration_file)
except FileNotFoundError:
    config = dict()
