#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import argparse
from time import sleep, perf_counter
import logging
import json
import os
import traceback
from pathlib import Path
from datetime import datetime

from ifm3dpy import O3R
import numpy as np

from oem_logging import setup_log_handler
from ods_stream import ODSStream
from zone_server_config import ZoneServerConfig
from bootup_monitor import monitor_bootup
from get_diagnostic import O3RDiagnostic
from adapters.data_models import ZoneSet
# from rotating_logger import setup_log_handler


# The log file handler will be configured in main()
logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)

PAUSE_ON_EXCEPTION = 5  # seconds to pause when something goes wrong
T_PER_NORMAL_OPERATION_STATUS_MESSAGE = (
    3600  # seconds to wait between saving log message about normal operation
)
USE_STRING_STATUS_UPDATE = False
ODS_DATA_COLLECTION_TIMEOUT = 5


# >>>>>>>>>>>>>>>> These functions loop over the corresponding adapter functions
def set_vpu_status(adapters: list, vpu_status):
    for adapter in adapters:
        adapter.set_vpu_status(vpu_status)


def set_zones_occ(adapters: list, occupancy):
    for adapter in adapters:
        adapter.set_zones_occ(occupancy)


def set_zones(adapters: list, zone_setting):
    for adapter in adapters:
        adapter.set_zones(zone_setting)


def push(adapters: list):
    for adapter in adapters:
        adapter.push()


# <<<<<<<<<<<<<<<<<<


def event_report(
    e: Exception = None,
    ctrl=None,
    adapters: list = None,
    o3r=None,
    status_desc: str = None,
    config_err: str = None,
    VPU_err: str = None,
    CTRL_err: str = None,
    catch_id=0,
):
    tb = traceback.format_exc()

    subsystem_errors = ""
    for subsystem, err in {
        "conf": config_err,
        "VPU": VPU_err,
        "CTRL": CTRL_err,
    }.items():
        if err:
            subsystem_errors += f" - {subsystem}_err: {err}"
            if not status_desc:
                status_desc = f"{subsystem}ERR: {err}"
    try:
        max_len_for_diagnostic_report = 3000
        if o3r:
            diagnostic_items = O3RDiagnostic(
                o3r).get_filtered_diagnostic_msgs()
        else:
            diagnostic_items = []
        elipsis = {1: "...", 0: ""}[
            int((len(str(diagnostic_items)) > max_len_for_diagnostic_report))
        ]
        report = f"{status_desc}{subsystem_errors}\ndiag_events:{str(diagnostic_items[:500])}{elipsis}"
    except Exception as diag_collection_err:
        report = f"{status_desc}{subsystem_errors}\ndiag_events could not be collected due to: {diag_collection_err} "

    if e is not None:
        logger.exception(f"{report}\n{tb}")

        try:
            if ctrl is not None and type(e) == Exception:
                ctrl.report_issue(catch_id, status_desc)
        except Exception as e:
            logger.info(f"Unable to report VPU issue to controller")
        sleep(PAUSE_ON_EXCEPTION)
    else:
        logger.info(report)
    # Worst case scenarios... reboot VPU
    # Unknown exceptions do not have a clear safe means of correction
    if (e is not None) and "importlib" in str(traceback.format_exc()):
        logger.info("Rebooting to fix unknown fault")
        sleep(1)
        o3r.reboot()


def setup_adapters(config_json) -> tuple:
    adapters = None
    controller = None
    while (not adapters) or (not controller):
        try:
            adapter_configs = config_json["adapters"]
            adapters = []

            for adapter_config in adapter_configs:
                adapter_handle = None

                adapter_type = adapter_config["type"]

                # import adapter-specific code and initialize adapter
                exec(f"from adapters.{adapter_type} import {adapter_type}")
                adapter_handle = eval(
                    f'{adapter_type}.Adapter(**adapter_config["params"])'
                )

                if adapter_handle:
                    if adapter_config["params"]["reciever"]:
                        adapters.append(adapter_handle)
                    if adapter_config["params"]["controller"]:
                        controller = adapter_handle
                print(adapter_handle)
        except Exception as e:
            CTRL_err = "Generic adapter setup failure... see traceback."
            event_report(
                CTRL_err=CTRL_err,
                e=e,
            )
    return controller, adapters


def setup_vpu(
    config_json, controller, adapters, n_frame_grabber_timeouts_in_a_row, mocking_ods
) -> tuple:
    while True:
        try:
            # Load VPU address
            if "in_docker" in os.environ and os.environ["in_docker"] == "true":
                VPU_addr = "172.17.0.1"
            else:
                VPU_addr = config_json["Eth0"]
            logger.info("Starting connection to VPU")
            o3r = O3R(VPU_addr)
            if not mocking_ods:
                monitor_bootup(o3r, VPU_addr)
            # TODO validate whether vpu is prepared for ods (are necessary cameras present)

            if n_frame_grabber_timeouts_in_a_row > 0 and not mocking_ods:
                logger.info(
                    f"Framegrabber timouts in a row: {n_frame_grabber_timeouts_in_a_row}"
                )
                if n_frame_grabber_timeouts_in_a_row == 2:
                    # TODO: save error state of the framegrabber
                    logger.info("resetting configurations")
                    o3r.reset("/ports")
                    o3r.reset("/applications")
                    sleep(PAUSE_ON_EXCEPTION)
                # after 4th attempt, reboot o3r
                elif n_frame_grabber_timeouts_in_a_row == 4:
                    # TODO: save error state of the framegrabber
                    logger.info("rebooting the VPU")
                    sleep(1)
                    o3r.reboot()
                    sleep(10)

            ods_config = ZoneServerConfig(o3r, config_json, mocking_ods)
            logger.debug("About to configure")
            if not mocking_ods:
                ods_config.initialize_ods()
            logger.debug("Initial configuration loaded")

            # Init the ODS object(s) and start the data stream(s)
            if not mocking_ods:
                ods_streams = {
                    view_name: ODSStream(o3r=o3r, app_name=app_name)
                    for app_name, view_name in ods_config.app_dict.items()
                }
                for stream in ods_streams.values():
                    stream.start_ods_stream()
            else:
                ods_streams = {}
            return o3r, ods_config, ods_streams
        except Exception as e:
            VPU_err = f"Generic vpu setup failure... see traceback"
            o3r = None
            event_report(
                e=e,
                ctrl=controller,
                adapters=adapters,
                VPU_err=VPU_err,
                o3r=o3r,
                catch_id=0,
            )
            sleep(PAUSE_ON_EXCEPTION)
            continue


def main(config_relative_path: str = "configs/config.json", mocking_ods: bool = False):
    n_frame_grabber_timeouts_in_a_row = 0

    try:
        abs_config_path = Path(__file__).parent.parent / config_relative_path
        with open(abs_config_path, "r") as f:
            config_json = json.load(f)
    except:
        sleep(10e8)  # don't allow the program to continue if there's a config issue

    in_docker = os.environ.get("IN_DOCKER", "0") in ["1", "True", "true", "y"]

    ts_format = "%y.%m.%d_%H.%M.%S%z"
    now = datetime.now().astimezone()
    now_local_ts = now.strftime(ts_format)

    msg = "Running example script oem_logging.py"
    if in_docker:
        msg += " from a docker container!"

        if "total_cached_log_size" in config_json:
            total_cached_log_size = config_json["total_cached_log_size"]
        else:
            total_cached_log_size = 0

        # If running in docker, check that the system clock is synchronized
        VPU_address_in_docker = "127.17.0.1"
        o3r = O3R(VPU_address_in_docker)
        try:
            clock_is_synced = o3r.get(
            )["device"]["clock"]["sntp"]["systemClockSynchronized"]
        except:
            clock_is_synced = False
        # If the clock is not synced, the log file name will just be the next highest integer
        if not clock_is_synced:
            now_local_ts = None
    else:
        o3r = O3R(config_json["VPU_address_for_deployment"])
        msg += " from a local machine!"
        total_cached_log_size = 1e10  # 10 GB on a local machine

    setup_log_handler(
        logger,
        total_cached_log_size=total_cached_log_size,
        log_dir=str(Path(__file__).parent.parent / "logs"),
        log_series_name="zone_server",
        t_initialized=now_local_ts)

    controller, adapters = setup_adapters(config_json)

    o3r, zone_server_config, ods_streams = setup_vpu(
        config_json=config_json,
        adapters=adapters,
        controller=controller,
        n_frame_grabber_timeouts_in_a_row=n_frame_grabber_timeouts_in_a_row,
        mocking_ods=mocking_ods,
    )
    initialize_adapter_state = True

    start_of_frame_loop = perf_counter()
    t_last_push = start_of_frame_loop
    n_status_log_messages_sent = 0
    frame_idx = -1

    zone_setting = ZoneSet(index=0)
    set_vpu_status(adapters, "IDLE")
    set_zones(adapters, zone_setting)
    set_zones_occ(adapters, [1, 1, 1])
    controller_ODS_state = "IDLE"
    event_report(status_desc="ODS set to 'IDLE'")

    while True:
        if initialize_adapter_state:
            zone_setting = ZoneSet(index=0)
            while True:
                try:
                    set_vpu_status(adapters, "IDLE")
                    set_zones(adapters, zone_setting)
                    set_zones_occ(adapters, [1, 1, 1])
                    controller_ODS_state = "IDLE"
                    break
                except Exception as e:
                    CTRL_err = f"No zone idx found from controller"
                    event_report(
                        e=e,
                        CTRL_err=CTRL_err,
                        o3r=o3r,
                    )
            initialize_adapter_state = False

        # Check zone setting
        last_zone_setting = zone_setting
        try:
            zone_setting = controller.recv()
        except Exception as e:
            event_report(
                e=e,
                CTRL_err="no zone idx found from controller",
                o3r=o3r,
            )
            controller, adapters = setup_adapters(config_json)
            initialize_adapter_state = True
            continue
        zone_setting_updated = last_zone_setting != zone_setting

        if (
            isinstance(zone_setting, ZoneSet)
            and zone_setting.index != 0
            and (not str(zone_setting.index) in zone_server_config.get_zones_LUT())
        ):
            logger.info(
                f"invalid zone_idx provided #{zone_setting}.. Setting to 0")
            zone_setting = ZoneSet(index=0)

        # TODO for firmware 1.1.X set to conf rather than idle
        system_should_be_idle = (
            isinstance(zone_setting, ZoneSet) and zone_setting.index == 0
        )
        if system_should_be_idle:
            # zone_idx of zero sets ods to idle for power saving
            try:
                if zone_setting_updated:
                    if controller_ODS_state == "RUN":
                        set_vpu_status(adapters, "IDLE")
                        set_zones(adapters, zone_setting)
                        set_zones_occ(adapters, [1, 1, 1])
                        controller_ODS_state = "IDLE"
                        event_report(status_desc="ODS set to 'IDLE'")
                    zone_server_config.set_ods_state("IDLE")
            except Exception as e:
                event_report(
                    e=e, ctrl=controller, o3r=o3r, VPU_err="Err setting ODS to 'IDLE'"
                )
                o3r, zone_server_config, ods_streams = setup_vpu(
                    config_json=config_json,
                    adapters=adapters,
                    controller=controller,
                    n_frame_grabber_timeouts_in_a_row=n_frame_grabber_timeouts_in_a_row,
                    mocking_ods=mocking_ods,
                )
                initialize_adapter_state = True
                continue
        else:  # zone setting matches a valid zone configuration
            # set zone config
            try:
                if zone_setting_updated:
                    zone_server_config.apply_zone_settings(zone_setting)
                    zone_server_config.set_ods_state("RUN")
                    set_vpu_status(adapters, "RUN")
                    set_zones(adapters, zone_setting)
                    controller_ODS_state = "RUN"
                zone_setting_updated = False
            except Exception as e:
                VPU_err = f"Err setting zone config"
                event_report(e=e, ctrl=controller, VPU_err=VPU_err)
                o3r, zone_server_config, ods_streams = setup_vpu(
                    config_json=config_json,
                    adapters=adapters,
                    controller=controller,
                    n_frame_grabber_timeouts_in_a_row=n_frame_grabber_timeouts_in_a_row,
                    mocking_ods=mocking_ods,
                )
                initialize_adapter_state = True
                continue
            # set ODS to run if it is not yet running
            try:
                if controller_ODS_state == "IDLE":
                    zone_server_config.set_ods_state("RUN")
                    set_vpu_status(adapters, "RUN")
                    set_zones(adapters, zone_setting)
                    controller_ODS_state = "RUN"
                    event_report(status_desc="ODS set to 'RUN'")
            except Exception as e:
                VPU_err = f"failed to set ODS to run"
                event_report(e=e, ctrl=controller, o3r=o3r, VPU_err=VPU_err)
                o3r, zone_server_config, ods_streams = setup_vpu(
                    config_json=config_json,
                    adapters=adapters,
                    controller=controller,
                    n_frame_grabber_timeouts_in_a_row=n_frame_grabber_timeouts_in_a_row,
                    mocking_ods=mocking_ods,
                )
                initialize_adapter_state = True
                continue

            # check zone occupancy
            try:
                if not mocking_ods:
                    zone_occupied = ods_streams[
                        zone_server_config.active_view
                    ].get_zone_occupancy(ODS_DATA_COLLECTION_TIMEOUT)
                else:
                    zone_occupied = np.int8(np.random.rand(3) * 2)
                set_zones_occ(adapters, zone_occupied.tolist())
                logger.debug(f"Set {zone_setting}:{zone_occupied}")
                n_frame_grabber_timeouts_in_a_row = 0
            except Exception as e:
                n_frame_grabber_timeouts_in_a_row += 1
                VPU_err = f"Err decoding ODS zone data"
                event_report(
                    e=e,
                    ctrl=controller,
                    o3r=o3r,
                    VPU_err=VPU_err,
                )
                o3r, zone_server_config, ods_streams = setup_vpu(
                    config_json=config_json,
                    adapters=adapters,
                    controller=controller,
                    n_frame_grabber_timeouts_in_a_row=n_frame_grabber_timeouts_in_a_row,
                    mocking_ods=mocking_ods,
                )
                initialize_adapter_state = True
                continue

        # Push data to recievers (if adapter requires a trigger to send data)
        try:
            if system_should_be_idle or mocking_ods:
                t_since_last_push = perf_counter() - t_last_push
                if t_since_last_push < 0.045:
                    sleep(0.048 - t_since_last_push)
            push(adapters)
            t_last_push = perf_counter()
        except Exception as e:
            CTRL_err = f"Error sending data to recievers"
            event_report(
                e=e,
                o3r=o3r,
                CTRL_err=CTRL_err,
            )
            break

        # periodically log current status
        frame_idx += 1
        if (
            perf_counter() - start_of_frame_loop
        ) / T_PER_NORMAL_OPERATION_STATUS_MESSAGE > n_status_log_messages_sent:
            n_status_log_messages_sent += 1
            event_report(
                o3r=o3r,
                status_desc=f"ODS state: '{zone_server_config.ods_state}', zone_setting: {zone_setting}",
            )


if __name__ == "__main__":
    # Define argument to get path to config file

    config_dir = Path(__file__).parent.parent / "configs"
    try:
        with open(config_dir / "which_config", "r") as f:
            which_config = f.read().strip()
    except:
        which_config = "configs/config.json"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="path to config file (default: configs/config.json)",
        default=which_config,
    )
    parser.add_argument(
        "--mocking",
        help="0/1 whether or not to mock the behavior of ODS",
        default=0,
    )
    args = parser.parse_args()

    main(args.config, args.mocking)
