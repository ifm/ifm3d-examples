# -*- coding: utf-8 -*-
import argparse
import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import jsonpointer
import jsonschema
from ifm3dpy import O3R
from jsonpointer import JsonPointer

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

TYPE_MAPPING = {
    "string": str,
    "boolean": bool,
    "integer": int,
    "float": float,
}

BARE_CONFIGURATIONS = {
    "ods": {
        "class": "ods",
        "name": "Get Schema",
        "state": "CONF",
    },
    "mcc": {
        "class": "mcc",
        "name": "Get Schema",
        "state": "CONF",
    },
    "pds": {
        "class": "pds",
        "name": "Get Schema",
        "state": "CONF",
    },
}


class VPUConfiguration:
    def __init__(self, configuration: Dict):
        self.configuration = configuration

    @property
    def instances(self) -> Dict:
        return self.configuration["applications"]["instances"]

    @property
    def applications(self) -> List[str]:
        return [app["class"] for app in self.instances.values()]

    @property
    def application_schemas(self) -> List[Dict]:
        applications = []
        classes: Dict[Dict] = self.configuration["applications"]["classes"]
        for app in classes:
            if app.get("instanceSchema", None) is not None:
                applications.append(app["instanceSchema"])
        return applications

    def validate(self, schema: Dict) -> None:
        jsonschema.validate(self.configuration, schema)

    def update_key(self, conf_path: JsonPointer, value: Any) -> None:
        jsonpointer.set_pointer(self.configuration, conf_path, value)

    def remove_key(self, path: JsonPointer) -> Any:
        def recursivce_remove(var: Dict, path: JsonPointer) -> Any:
            if len(path.parts) == 1:
                return var.pop(path.parts[0])
            else:
                return recursivce_remove(
                    var[path.parts[0]], JsonPointer.from_parts(path.parts[1:])
                )

        return recursivce_remove(self.configuration, path)


def create_basic_applications(o3r: O3R, applications: List[str]) -> List[str]:
    """
    Create basic applications on the device. After this it is possible to get the application schema with configuration.

    Args:
        applications (List[str]): The list of applications to create.

    Returns:
        None
    """
    current_apps = o3r.get(["/applications/instances"])
    tmp_apps = []
    try:
        # Get the last application number to not overwrite existing applications
        last_app = [
            app
            for app in current_apps["applications"]["instances"].keys()
            if app.startswith("app")
        ][-1]
        last_app_number = int(last_app[3:]) + 1
    except IndexError:
        last_app_number = 0
    for app in applications:
        LOGGER.debug(f"Create temporary application {app}")

        config = {
            "applications": {
                "instances": {f"app{last_app_number}": BARE_CONFIGURATIONS[app]}
            }
        }
        o3r.set(config)
        tmp_apps.append(f"app{last_app_number}")

        last_app_number += 1
    return tmp_apps


def convert_to_type(value: Any, type_name: str) -> Any:
    """
    Convert the given value to the specified type.

    Args:
        value (Any): The value to be converted.
        type_name (str): The name of the type to convert the value to.

    Returns:
        Any: The converted value.

    Raises:
        TypeError: If the type name is unknown.
    """
    if type_name in TYPE_MAPPING:
        return TYPE_MAPPING[type_name](value)
    else:
        raise TypeError(f"Unknown type name: {type_name}")


def parse_to_schema(conf: VPUConfiguration, schema: Dict) -> List[Tuple[str, Any]]:
    """
    Try to update the configuration file to match the new schema.

    Args:
        conf (VPUConfiguration): The configuration file to update.
        schema (dict): The new schema.

    Returns:
        List: The deleted configuration paths.
    """
    deleted_configurations = []
    while True:
        try:
            conf.validate(schema)
            break
        except jsonschema.ValidationError as error:
            conf_path = "/" + "/".join(str(part) for part in error.absolute_path)
            schema_path = "/" + "/".join(
                str(part) for part in error.absolute_schema_path
            )

            if error.validator == "type":
                LOGGER.debug(
                    f"Type mismatch {conf_path} {type(error.instance)} -> {error.validator_value}"
                )

                converted_val = convert_to_type(error.instance, error.validator_value)
                conf.update_key(conf_path, converted_val)

            elif error.validator == "additionalProperties":
                # Remove the additional properties not the parent key
                LOGGER.debug(f"Additional property in {conf_path}")

                keys = copy.copy(list(error.instance.keys()))
                for key in keys:
                    if key in error.message:
                        value = conf.remove_key(JsonPointer(f"{conf_path}/{key}"))
                        deleted_configurations.append((f"{conf_path}/{key}", value))

                        LOGGER.debug(f"Delete key:val {conf_path}/{key}: {value}")
            else:
                LOGGER.debug(f"Can not resolve error {schema_path}")

                value = conf.remove_key(JsonPointer(conf_path))
                deleted_configurations.append((conf_path, value))

                LOGGER.debug(f"Delete key:val {conf_path}: {value}")

    return deleted_configurations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Try to apply an old FW configuration file to an new FW"
    )
    parser.add_argument(
        "-i",
        "--input",
        help="The old configuration file to update",
        type=Path,
        required=True,
        dest="input",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path where to save the new configuration. If none it would be printed to std out",
        type=Path,
        required=False,
        default=None,
        dest="output",
    )
    parser.add_argument(
        "--ip",
        help="The IP address of the device",
        type=str,
        required=False,
        default="192.168.0.69",
    )
    parser.add_argument(
        "--not-apply",
        help="Do not apply the updated configuration file to the device",
        action="store_true",
        default=False,
        dest="n_apply",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase output verbosity",
        action="count",
        default=0,
        dest="verbose",
    )
    parser.add_argument(
        "--log-file",
        help="The file to save relevant output",
        type=Path,
        required=False,
        default=Path("deleted_configurations.log"),
        dest="log_file",
    )
    args = parser.parse_args()

    LOGGER.setLevel(logging.INFO - args.verbose * 10)

    try:
        configuration: dict = json.loads(args.input.read_text())
    except json.decoder.JSONDecodeError as error:
        LOGGER.error(f"Can not parse the configuration file: {error}")
        exit(1)

    o3r = O3R(args.ip)
    conf = VPUConfiguration(configuration)

    # Create temporary applications to get the schema
    old_apps = conf.applications
    tmp_apps = create_basic_applications(o3r, conf.applications)

    schema = o3r.get_schema()
    deleted_paths = parse_to_schema(conf, schema)

    for app in tmp_apps:
        LOGGER.debug(f"Delete temporary application {app}")
        o3r.reset(f"/applications/instances/{app}")

    # Print the deleted configurations and save them to a file
    if deleted_paths:
        deleted_log_path = Path("deleted_configurations.log")
        LOGGER.warning(
            "The following configurations were deleted - used default values"
        )
        LOGGER.warning(f"The completet output is saved to {args.log_file.absolute()}")
        args.log_file.write_text(json.dumps(deleted_paths, indent=3))
        for deleted in deleted_paths:
            LOGGER.warning(deleted[0])

    if args.output is not None:
        LOGGER.info(f"Save the updated configuration to {args.output}")
        args.output.write_text(json.dumps(configuration, indent=4))
    else:
        LOGGER.info(json.dumps(configuration, indent=4))

    if not args.n_apply:
        try:
            LOGGER.info("Apply the updated configuration to the device")
            o3r.set(configuration)
        except Exception as error:
            LOGGER.error(f"Can not apply the configuration to the device: {error}")
            exit(1)
