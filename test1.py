import json

with open(r'json/scores.json', 'r') as fp:
    quality_data = json.load(fp)


midval = list(quality_data.values())