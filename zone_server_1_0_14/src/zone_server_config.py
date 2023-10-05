#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy import O3R
import logging
import time
from adapters.data_models import ZoneSet, AdHocZoneSetting, ZONES_ID_WHEN_UNCONFIGURED


logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

def mergedicts(snippet_1:dict, snippet_2:dict):
    for k in set(snippet_1.keys()).union(snippet_2.keys()):
        if k in snippet_1 and k in snippet_2:
            if isinstance(snippet_1[k], dict) and isinstance(snippet_2[k], dict):
                yield (k, dict(mergedicts(snippet_1[k], snippet_2[k])))
            else:
                # If one of the values is not a dict, you can't continue merging it.
                # Value from second dict overrides one in first and we move on.
                yield (k, snippet_2[k])
                # Alternatively, replace this with exception raiser to alert you of value conflicts
        elif k in snippet_1:
            yield (k, snippet_1[k])
        else:
            yield (k, snippet_2[k])

class ZoneServerConfig:
    """
    Sample Wrapper for ODS configuration

    This should manage changing of camera views and changing of zones.

    When object is initialized, no changes are made to the device.

    ZoneServerConfig.app_dict -> shows {app:view}
    """

    def __init__(self, o3r: O3R, config_json, mocking_ods: bool = False) -> None:
        self.current_zone_setting = ZoneSet(index=-1)
        self.o3r = o3r
        self.config_json = config_json
        self.mocking_ods = mocking_ods

        # define 'idle' zone configuration
        arbitrary_zone_set = list(self.config_json["zones"].values())[0]
        self.config_json["zones"]["0"] = arbitrary_zone_set.copy()
        self.idle_zones = [[[-5, -5], [-5, 5], [5, 5], [5, -5]]] * 3
        for i, zone in enumerate(self.idle_zones):
            self.config_json["zones"]["0"][f"zone{i}"] = zone

        self.ods_state = "CONF"
        self.active_view = None
        self.view_dict = {}
        self.app_dict = {}
        self.port_dict = {}
        self.default_view = list(config_json["views"])[0]

        logger.info("ODS configuration(s) loaded but not yet initialized")

    def get_zones_LUT(self):
        return self.config_json["zones"]

    def update_zones_LUT(self, idx: int, zones: dict):
        self.config_json["zones"][str(idx)] = zones
        # print(self.config_json["zones"])

    def initialize_ods(self) -> None:
        present_ports = list(self.o3r.get(["/ports"])["ports"].keys())
        # set camera positions and turn all cameras to CONF
        port_config = {"ports": self.config_json["ports"]}
        for port in present_ports:
            if not port in port_config["ports"]:
                port_config["ports"][port] = {}
            port_config["ports"][port].update({"state": "CONF"})
        self.o3r.set({"ports": self.config_json["ports"]})



        n_views = len(self.config_json["views"])
        for i, view_name in enumerate(self.config_json["views"].keys()):
            self.view_dict[view_name] = f"app{i}"
            self.app_dict[
                f"app{i}"
            ] = view_name
            self.port_dict[view_name] = [int(port[-1]) for port in self.config_json["views"][view_name]["ports"]]

            # update dictionaries to be consistent with schemas
            zone_config = self.get_zone_config_dict_from_zone_setting(
                zone_setting=ZoneSet(index=0), view=view_name
            )
            config_snippet = {
                "applications": {
                    "instances": {
                        self.view_dict[view_name]: dict(mergedicts({
                            "class": "ods",
                            "state": "CONF",
                            "configuration": {
                                "grid": {
                                    "maxHeight": zone_config["maxHeight"],
                                },
                                "zones": {
                                    "zoneConfigID": int(zone_config["id"]),
                                    "zoneCoordinates": [
                                        zone_config[f"zone{i}"] for i in range(3)
                                    ],
                                },
                            },
                        },self.config_json["views"][view_name]))
                    }
                }
            }
            logger.debug(config_snippet)
            logger.debug(
                f"Initializing view:'{view_name}' (app_name:'{self.view_dict[view_name]}')"
            )
            # load config to VPU (as CONF)
            time.sleep(0.5)
            self.o3r.set(config_snippet)

        logger.debug("Initialized ODSConfig")
        self.get_active_view()  # check for existing applications

    def change_view(self, view_name: str) -> None:
        if self.get_active_view():
            # set current view to IDLE
            self.set_ods_state("IDLE")
            # change self.active_view
            self.active_view = view_name
            # set next view to RUN
            self.set_ods_state("RUN")
        else:
            self.active_view = view_name

    def get_zone_config_dict_from_zone_setting(
        self,
        zone_setting=ZoneSet(index=0),
        view: str = None,
    ) -> dict:
        if view is None:
            view = self.active_view
        zone_config = {"id": ZONES_ID_WHEN_UNCONFIGURED}
        if isinstance(zone_setting, ZoneSet):
            zone_config["id"] = zone_setting.index
            if str(zone_setting.index) in self.config_json["zones"]:
                zone_config.update(self.config_json["zones"][str(zone_setting.index)])
            else:
                zone_config.update(self.config_json["zones"]["0"])
        elif isinstance(zone_setting, AdHocZoneSetting):
            zone_config.update(zone_setting.dict())
            
        return zone_config

    def define_o3r_zone_config(
        self,
        zone_setting=ZoneSet(index=0),
        zone_config: dict = None,
        view: str = None,
    ) -> dict:
        """
        Builds the zone configuration automatically.
        A zone point: [x,y] (in simple example x is ahead, y is left and right)

        Measurement is in meters.

        Returns:
            dict: The O3R config snippet to be loaded onto the VPU
        """
        if not zone_config:
            zone_config = self.get_zone_config_dict_from_zone_setting(
                zone_setting, view
            )
        if "id" not in zone_config:
            zone_config["id"] = ZONES_ID_WHEN_UNCONFIGURED

        config_snippet = {
            "applications": {
                "instances": {
                    self.view_dict[self.active_view]: {
                        "configuration": {
                            "grid": {
                                "maxHeight": zone_config["maxHeight"],
                            },
                            "zones": {
                                "zoneConfigID": int(zone_config["id"]),
                                "zoneCoordinates": [
                                    zone_config[f"zone{i}"] for i in range(3)
                                ],
                            },
                        }
                    }
                }
            }
        }

        return config_snippet

    def apply_zone_settings(self, zone_setting):
        logger.debug(f"Applying zone: {zone_setting}")
        if not self.mocking_ods:
            if self.current_zone_setting != zone_setting:
                self.current_zone_setting = zone_setting

                idle_mode = False

                if isinstance(zone_setting, AdHocZoneSetting):
                    if zone_setting.view:
                        self.change_view(zone_setting.view)
                    else:
                        self.change_view(self.default_view)
                elif isinstance(zone_setting, ZoneSet):
                    if zone_setting.index == 0:
                        idle_mode = True
                    else:
                        self.change_view(
                            self.get_zones_LUT()[str(zone_setting.index)]["view"]
                        )

                if not idle_mode:
                    zone_config_snippet = self.define_o3r_zone_config(
                        zone_setting=zone_setting
                    )
                    self.o3r.set(zone_config_snippet)
            else:
                logger.debug("No change in zone id")
                pass

    def set_ods_state(self, state: str, view=None):
        """
        Writes update to VPU config to alter ods state.

        Args:
            state (str): "IDLE", "CONF", "RUN", "ERR"
        """
        if not self.mocking_ods:
            if view is None:
                if not self.active_view:
                    self.active_view = self.default_view
                view = self.active_view

            state_config = {
                "applications": {"instances": {self.view_dict[view]: {"state": state}}}
            }
            self.o3r.set(state_config)
        self.ods_state = state

    def close_apps(self):
        self.o3r.reset("/applications")

    def get_active_view(self, latest_config: dict = None) -> str:
        active_view = None

        if latest_config is None:
            latest_config = self.o3r.get()

        if (
            "applications" in latest_config
            and "instances" in latest_config["applications"]
        ):
            apps = latest_config["applications"]["instances"]

            for app_name, app_data in apps.items():
                if app_name not in list(
                    self.view_dict.values()
                ):  # checking for previously initialized applications
                    self.view_dict[app_name] = app_name
                    self.app_dict[app_name] = app_name
                if "state" in app_data and app_data["state"] == "RUN":
                    active_view = self.app_dict[app_name]
            self.active_view = active_view

        return active_view

    def get_active_app(self, latest_config: dict = None):
        self.get_active_view(latest_config)
        if self.active_view:
            return self.view_dict[self.active_view]
        else:
            None
