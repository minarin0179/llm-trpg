import yaml

with open('src/setting.yml', 'r') as file:
    config = yaml.safe_load(file)

    for key, value in config.items():
        globals()[key] = value

print(SCENARIO_PATH)
