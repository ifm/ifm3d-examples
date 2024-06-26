#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
# %%############################################
# Showcases a typical sequence of an ODS application running
# from the initial configuration to the "while true" streaming of data
######################################################################

# Imports
import logging
import numpy as np
from ifm3dpy.device import O3R

from ovp8xxexamples.core.diagnostic import O3RDiagnostic
from ovp8xxexamples.core.bootup_monitor import BootUpMonitor
from ovp8xxexamples.ods.ods_config import validate_json, load_config_from_file
from ovp8xxexamples.ods.ods_stream import ODSStream
from ovp8xxexamples.ods.ods_visualization import OCVWindow, ODSViz


def main(ip, log_to_file, ods_cfg_file, calib_cfg_file):
    # %% Initialization of basic objects
    o3r = O3R(ip)
    logger = logging.getLogger(__name__)
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    # %%######################################
    # Make sure boot up sequence is completed
    #########################################
    bootup_monitor = BootUpMonitor(o3r)
    bootup_monitor.monitor_VPU_bootup()

    # %%######################################
    # Check the diagnostic for any critical errors
    #########################################
    diag = O3RDiagnostic(o3r=o3r, log_to_file=log_to_file)
    for err in diag.get_diagnostic_filtered({"state": "active"})["events"]:
        logger.error(f"Active error: {err['id']}, {err['name']}")
    logger.info("Review any active errors before continuing.")

    # %%######################################
    # Start the async diag
    #########################################
    diag.start_async_diag()

    # %%######################################
    # Configure the ODS application
    #########################################
    o3r.reset("/applications")
    schema = o3r.get_schema()

    # Set the camera extrinsics so that ODS knows where everything is
    config_snippet_extrinsics = load_config_from_file(calib_cfg_file)
    validate_json(schema, config_snippet_extrinsics)
    o3r.set(config_snippet_extrinsics)

    # Initialize the app
    config_snippet_new_ods_app = load_config_from_file(ods_cfg_file)
    validate_json(schema, config_snippet_new_ods_app)
    o3r.set(config_snippet_new_ods_app)

    input("Press enter to run the ODS application\n")
    # Set the app state to RUN
    o3r.set({"applications": {"instances": {"app0": {"state": "RUN"}}}})

    # %%######################################
    # Start streaming data
    #########################################
    ods_stream = ODSStream(o3r=o3r, app_name="app0", buffer_length=1, timeout=200)
    ods_stream.start_ods_stream()

    # %%######################################
    # Display data (no interactivity)
    #########################################

    window = OCVWindow(
        "ODS output - Occupancy grid, zones and diagnostic. Press 'q' to exit."
    )
    window.open()
    visualizer = ODSViz(o3r)
    try:
        while window.window_created:
            # Collect ODS output
            zones = ods_stream.get_zones().zone_occupied
            raw_occupancy_grid = ods_stream.get_occupancy_grid().image

            # Generate a pretty visual
            ods_visualization = visualizer.render_visual(raw_occupancy_grid, zones)
            window.update_image(ods_visualization)

    except Exception as e:
        logger.info("Viewing interrupted, turning off viewer.")
        window.destroy()
        raise e

    # %%######################################
    # Display data and toggle active cameras using number keys
    #########################################
    app0 = o3r.get(["/applications/instances/app0"])["applications"]["instances"][
        "app0"
    ]
    available_3d_port_ns = [
        int(port[-1]) for port in app0["ports"] if int(port[-1]) < 6
    ]
    max_active_cameras = app0["configuration"]["maxNumSimultaneousCameras"]
    active_cameras = [
        port[-1]
        for port in o3r.get(["/applications/instances/app0/configuration/activePorts"])[
            "applications"
        ]["instances"]["app0"]["configuration"]["activePorts"]
    ]

    window = OCVWindow("ODS output - Occupancy grid, zones and diagnostic")
    window.open()
    visualizer = ODSViz(
        o3r,
        "Hints:\nToggle cameras by typing\ntheir corresponding port number.\nPress 'q' to quit.",
    )
    try:
        while window.window_created:
            # Collect ODS output
            if active_cameras:
                zones = ods_stream.get_zones().zone_occupied
                raw_occupancy_grid = ods_stream.get_occupancy_grid().image
            else:
                zones = [1, 1, 1]
                raw_occupancy_grid = np.ones((200, 200), np.uint8) * 51

            # Generate a pretty visual
            ods_visualization = visualizer.render_visual(raw_occupancy_grid, zones)
            window.update_image(ods_visualization)

            # toggle cameras based on keyboard input
            if window.keypress > 0 and chr(window.keypress) in [
                str(port) for port in available_3d_port_ns
            ]:
                active_cameras = [
                    port[-1]
                    for port in o3r.get(
                        ["/applications/instances/app0/configuration/activePorts"]
                    )["applications"]["instances"]["app0"]["configuration"][
                        "activePorts"
                    ]
                ]
                if chr(window.keypress) in active_cameras:
                    active_cameras.remove(chr(window.keypress))
                else:
                    if len(active_cameras) < max_active_cameras:
                        active_cameras.append(chr(window.keypress))
                    else:
                        continue
                logger.info(
                    f"Updating ODS application to change state of port {chr(window.keypress)}"
                )
                o3r.set(
                    {
                        "applications": {
                            "instances": {
                                "app0": {
                                    "configuration": {
                                        "activePorts": [
                                            "port" + port_n for port_n in active_cameras
                                        ]
                                    }
                                }
                            }
                        }
                    }
                )
                visualizer.get_active_ports()

    except Exception as e:
        logger.info("Viewing interrupted, turning off viewer.")
        window.destroy()
        raise e


# %%
if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        LOG_TO_FILE = config.LOG_TO_FILE
        CALIB_CFG_FILE = config.CALIB_CFG_FILE
        ODS_CFG_FILE = config.ODS_CFG_FILE
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        IP = "192.168.0.69"
        LOG_TO_FILE = False
        CALIB_CFG_FILE = "configs/extrinsic_two_heads.json"
        ODS_CFG_FILE = "configs/ods_two_heads_config.json"
        print(f"Choosing alternative parameters: IP = {IP}, LOG_TO_FILE = {LOG_TO_FILE}", f"CALIB_CFG_FILE = {CALIB_CFG_FILE}, ODS_CFG_FILE = {ODS_CFG_FILE}")

    main(
        ip=IP,
        log_to_file=LOG_TO_FILE,
        calib_cfg_file=CALIB_CFG_FILE,
        ods_cfg_file=ODS_CFG_FILE,
    )
