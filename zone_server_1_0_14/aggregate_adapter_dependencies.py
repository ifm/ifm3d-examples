
# This file get's called in the build process of the docker container so that the build process is decoupled from the needs of a particular project
import json
from pathlib import Path

# aggregate requirements.txts from each adapter referenced in "config/which_config"
project_dir = Path(__file__).parent
config_dir = project_dir / "configs"
config_path = project_dir
with open(config_dir / "which_config", "r") as f:
    path_to_config = f.read().split("/")
for file in path_to_config:
    config_path /= file
with open(config_path, "r") as f:
    config_json = json.load(f)
with open("requirements.txt", "r") as f:
    requirements = f.read()
for adapter in config_json["adapters"]:
    with open(project_dir/"src"/"adapters"/adapter["type"]/"requirements.txt","r")as f:
        requirements+= "\n"+ f.read()
with open("requirements.txt","w")as f:
    f.write(requirements)

