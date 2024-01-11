# %%###################################################################
# Showcases a typical sequence of an ODS application running
# from the initial configuration to the "while true" streaming of data
######################################################################

# Imports
from ods_visualization import OCVWindow, ODSViz
import logging

import numpy as np
from ifm3dpy.device import O3R

from bootup_monitor import BootUpMonitor
from diagnostic import O3RDiagnostic
from ods_config import validate_json, load_config_from_file
from ods_stream import ODSStream

# Initialization of basic objects
ADDR = "192.168.0.69"
o3r = O3R(ADDR)
logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.INFO)

# %%######################################
# Make sure boot up sequence is completed
#########################################
with BootUpMonitor(o3r) as bootup_monitor:
    try:
        bootup_monitor.monitor_VPU_bootup()
    except TimeoutError as err:
        raise err

# %%######################################
# Check the diagnostic for any critical errors
#########################################
diag = O3RDiagnostic(o3r=o3r, log_to_file=False)
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
config_snippet_extrinsics =load_config_from_file("configs/extrinsic_two_heads.json")
validate_json(schema, config_snippet_extrinsics)
o3r.set(config_snippet_extrinsics)

# Initialize the app
config_snippet_new_ods_app = load_config_from_file(
    "configs/ods_two_heads_config.json")
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
    "ODS output - Occupancy grid, zones and diagnostic. Press 'q' to exit.")
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
app0 = o3r.get(["/applications/instances/app0"]
               )["applications"]["instances"]["app0"]
available_3d_port_ns = [int(port[-1])
                        for port in app0["ports"] if int(port[-1]) < 6]
max_active_cameras = app0["configuration"]["maxNumSimultaneousCameras"]
active_cameras = [port[-1] for port in o3r.get(["/applications/instances/app0/configuration/activePorts"])[
    "applications"]["instances"]["app0"]["configuration"]["activePorts"]]

window = OCVWindow(
    "ODS output - Occupancy grid, zones and diagnostic")
window.open()
visualizer = ODSViz(
    o3r, "Hints:\nToggle cameras by typing\ntheir corresponding port number.\nPress 'q' to quit.")
try:
    while window.window_created:
        # Collect ODS output
        if active_cameras:
            zones = ods_stream.get_zones().zone_occupied
            raw_occupancy_grid = ods_stream.get_occupancy_grid().image
        else:
            zones = [1, 1, 1]
            raw_occupancy_grid = np.ones((200, 200), np.uint8)*51

        # Generate a pretty visual
        ods_visualization = visualizer.render_visual(raw_occupancy_grid, zones)
        window.update_image(ods_visualization)

        # toggle cameras based on keyboard input
        if window.keypress > 0 and chr(window.keypress) in [str(port) for port in available_3d_port_ns]:
            active_cameras = [port[-1] for port in o3r.get(["/applications/instances/app0/configuration/activePorts"])[
                "applications"]["instances"]["app0"]["configuration"]["activePorts"]]
            if chr(window.keypress) in active_cameras:
                active_cameras.remove(chr(window.keypress))
            else:
                if len(active_cameras) < max_active_cameras:
                    active_cameras.append(chr(window.keypress))
                else:
                    continue
            logger.info(f"Updating ODS application to change state of port {chr(window.keypress)}")
            o3r.set({
                "applications": {
                    "instances": {
                        "app0": {
                            "configuration": {
                                "activePorts": ["port"+port_n for port_n in active_cameras]
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
