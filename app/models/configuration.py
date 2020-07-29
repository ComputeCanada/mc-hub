from models.constants import CONFIGURATION_FILE_PATH
import json

try:
    with open(CONFIGURATION_FILE_PATH) as configuration_file:
        configuration = json.load(configuration_file)
except FileNotFoundError:
    configuration = dict()
