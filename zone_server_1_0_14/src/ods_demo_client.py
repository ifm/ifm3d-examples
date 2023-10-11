#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
#############################################
# This is an interactive desktop demonstration of the ODS system with dynamic zone configuration.
# Step 1: Plug a camera head in so that the 2D is connected to port0 and the 3D head is connected to port1. Power up the VPU, check that you can ping it
# Step 2: Install python dependencies from 'requirements.txt',
# Step 3: Try running from CLI/debugger or run python code 'cells' interactively by pressing "shift-enter" in editors like vscode/spyder/pycharm/etc. when code cells are separated by "#%%" delimiters...
##############################################

from ifm3dpy import O3R
import json
import ifm3dpy
import cv2

from get_diagnostic import O3RDiagnostic
from zone_server_config import ZoneServerConfig
from ods_stream import ODSStream
from adapters.data_models import ZoneSet, AdHocZoneSetting

import numpy as np
import time
from pathlib import Path
import sys
import argparse

# %% Configure the application using either interactive python or CLI arguments...
# Configuration of demo script
print(f"Using ifm3dpy v{ifm3dpy.__version__}")
if "ipykernel" in sys.modules:
    print("Running demo via interactive python script.")
    # configure script here if running using ipython:
    START_ODS = 1
    online = 1
    send_zone_config = 1
    close_previous_apps = 1
    # how many seconds to show live visualization, 0 for infinite
    visualization_duration = 0
    addr = "192.168.0.69"  # default is 192.168.0.69

    which_config = ""
    check_for_changed_vpu_state = 1
else:  # if running as script or via debugger
    print("Running demo via cli.")
    parser = argparse.ArgumentParser(
        description="ifm ods example",
    )
    parser.add_argument(
        "--IP", type=str, default="192.168.0.69", help="IP address to be used"
    )
    parser.add_argument(
        "--overwrite_apps",
        type=int,
        default=1,
        help="0 to leave existing apps alone, 1 to overwrite them.",
    )
    parser.add_argument(
        "--start_ods",
        type=int,
        default=1,
        help="whether or not to initialize ods.",
    )
    parser.add_argument(
        "--offline_mode",
        type=int,
        default=0,
        help="whether or not to connect to vpu",
    )
    parser.add_argument(
        "--send_zones",
        type=int,
        default=1,
        help="whether or not to update zones on vpu",
    )
    parser.add_argument("--which_config", type=str, default="")

    send_zone_config = 1
    args = parser.parse_args()
    START_ODS = args.start_ods
    close_previous_apps = bool(args.overwrite_apps)
    which_config = args.which_config
    online = not args.offline_mode
    addr = args.IP
    send_zone_config = args.send_zones

    visualization_duration = 0
    check_for_changed_vpu_state = 1

# Collect system configuration .json file
project_dir = Path(__file__).parent.parent
config_dir = project_dir / "configs"
config_path = project_dir
if which_config:
    path_to_config = which_config.split("/")
else:
    with open(config_dir / "which_config", "r") as f:
        path_to_config = f.read().split("/")
for file in path_to_config:
    config_path /= file
print(f'Using config: "{project_dir/config_path}"')
with open(config_path, "r") as f:
    config_json = json.load(f)

# %% Try connecting to VPU
# Connect to VPU
addr = config_json["Eth0"]
o3r = O3R(addr)
try:
    if online:
        config = o3r.get()
    print(f"VPU found at {addr}")
except:
    online = 0
    print(f"No VPU found at {addr}")


# Initialize the ODS configuration handler...
ods_config = ZoneServerConfig(o3r, config_json)

# config zones
o3r.set({"ports": ods_config.config_json["ports"]})

# %%
if START_ODS and online:
    if "applications" in config:
        if (
            "instances" in config["applications"]
            and config["applications"]["instances"]
        ):
            if close_previous_apps:
                ods_config.close_apps()
                print("Stopping current ods instance(s)")
                time.sleep(5)
                print("Restarting ODS")

                ods_config.initialize_ods()
                ods_config.set_ods_state("RUN")
                time.sleep(5)
            else:
                print("ODS already running")
                ods_config.get_active_view()
        else:
            ods_config = ZoneServerConfig(o3r, config_json)
            print("Starting ODS")
            ods_config.initialize_ods()
            print("ODS initialized")
            ods_config.set_ods_state("RUN")
            print("ODS running")
elif online and close_previous_apps:
    ods_config.close_apps()
    print("Setting camera configuration, but not setting up ODS")
    o3r.set({"ports": config_json["ports"]})
    # if ods is not running, then do not try to connect to the VPU
    online = False


# %%
if "atwater360_5x3d" in str(config_path): # When using a test configuration for a mobile base located at the ifm headquarters
    wide_angle = False
    ods_config.apply_zone_settings(zone_setting=ZoneSet(index=1))
    time.sleep(0.5)
    if wide_angle:
        ods_config.apply_zone_settings(zone_setting=ZoneSet(index=1))
        o3r.set(
            {"ports": {"port1": {"state": "RUN", "acquisition": {"channelValue": 10}}}}
        )
    else:
        ods_config.apply_zone_settings(zone_setting=ZoneSet(index=3))
        o3r.set(
            {"ports": {"port0": {"state": "RUN", "acquisition": {"channelValue": 5}}}}
        )

    o3r.set({"ports": {"port2": {"state": "RUN", "acquisition": {"channelValue": 15}}}})
    o3r.set({"ports": {"port3": {"state": "RUN", "acquisition": {"channelValue": 20}}}})
    o3r.set({"ports": {"port4": {"state": "RUN", "acquisition": {"channelValue": 15}}}})


# %%
# Initialize data streams
if online and (
    "applications" not in o3r.get() or "instances" not in o3r.get()["applications"]
):
    online = 0
    print("No ODS application is currently running... resuming script in offline mode")
if online:
    print("Initializing data streams.")
    ods_streams = {}
    for view_name, app_name in ods_config.view_dict.items():
        ods_streams[view_name] = ODSStream(o3r, buffer_length=5, app_name=app_name)
        ods_streams[view_name].start_ods_stream()

    ods_stream_list = list(ods_streams.keys())
    view_i = 0

    if send_zone_config:
        ods_config.change_view(ods_stream_list[view_i])

# %% Check for data about outline of vehicle for visualization purposes

# "vehicles" should define various vehicle parameters including the "extent" of the vehicles (the points defining the outline of the vehicle in x-y plane)
if "vehicles" in config_json:
    vehicles = config_json["vehicles"]
else:
    vehicles = []

# %% Define initial zone parameters

starting_depth = 0.5
starting_safety_margin = 0.2
starting_vehicle_i = 0
starting_height = 2
starting_zone_mode = 0
zone_modes = ["generated", "configured"]
starting_configured_zone_set_id_idx = 1
configured_zone_sets = ods_config.get_zones_LUT()
zone_set_ids = list(configured_zone_sets.keys())

vehicle_i = 0
zone_mode = starting_zone_mode
depth = starting_depth
safety_margin = starting_safety_margin
zone_set_id_i = starting_configured_zone_set_id_idx
center_of_rotation_offset = vehicles[vehicle_i]["center_of_rotation_offset"]
height = vehicles[vehicle_i]["height"]

FRAMES_PER_ZONE_CONFIG_RETRIEVAL_FROM_VPU = 5

# %% Define a helper function to define ODS zones based on keyboard input


def generate_zones(
    depth,
    safety_margin,
    vehicle_extent: dict,
    view: str,
    zone_config_id: int = 1000,
    max_height: float = 3,
):
    ymin = min([pt[1] for pt in vehicle_extent["extent"]]) - safety_margin
    ymax = max([pt[1] for pt in vehicle_extent["extent"]]) + safety_margin
    return AdHocZoneSetting(
        **{
            "zone0": [
                [0 * depth, ymin],
                [1 * depth, ymin],
                [1 * depth, ymax],
                [0 * depth, ymax],
            ],
            "zone1": [
                [1 * depth, ymin],
                [2 * depth, ymin],
                [2 * depth, ymax],
                [1 * depth, ymax],
            ],
            "zone2": [
                [2 * depth, ymin],
                [3 * depth, ymin],
                [3 * depth, ymax],
                [2 * depth, ymax],
            ],
            "view": view,
            "index": zone_config_id,
            "maxHeight": max_height,
        }
    )


# %% Generate initial zone configuration

zone_set = generate_zones(
    depth,
    safety_margin,
    vehicle_extent=vehicles[vehicle_i],
    view=ods_config.active_view,
    zone_config_id=2000,
)
print("Adding initial zone-set to VPU.")
if send_zone_config and online:
    ods_config.apply_zone_settings(zone_set)

# %% Prepare for pretty visualization and begin looping

# Set rate of adjustment for the zone parameters
adjustment_rate = 0.05
# Ratio of resolution of visualization to the resolution of occupancy grid (200x200):
upscale_factor = 4
# Colors of ((unoccupied zone),(occupied zone))
colors = (
    ((0, 0, 150), (0, 0, 255)),
    ((0, 150, 150), (0, 255, 255)),
    ((0, 150, 0), (0, 255, 0)),
)
# define window name
if not online:
    winname = "Zones"
else:
    winname = "Occupancy Grid + Zones"
occupancy_grid = np.ones((200 * upscale_factor, 200 * upscale_factor, 3), np.uint8) * 50
# Allow window to be resizeable
cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
# Update window (hanging windows get unstable on linux)
cv2.imshow(winname, occupancy_grid)
# Collect keypresses (more cv2 boilerplate):
k = cv2.waitKey(1) & 0xFF

# prep for using cv2.putText() method
font = cv2.FONT_HERSHEY_SIMPLEX
org = (10, 30)
fontScale = 0.6
text_color = (255, 255, 255)
thickness = 1.3
pixels_per_row_of_text = 25

# some variables used for periodic operations during loop
i_frames = 0
last_frame_collected_time = time.perf_counter()
start = time.perf_counter()

# initialize variables used to store output from ODS
zones_occupied = (1, 1, 1)
raw_occupancy_grid = np.zeros((200, 200), np.uint8) + 51

print("looping")
while (
    time.perf_counter() - start < visualization_duration or visualization_duration < 0.1
):
    # Check if data is available from ods. If so, update zone occupancy and raw_occupancy grid
    if online:
        active_view = ods_config.active_view
        if active_view:
            buffer_size = ods_streams[ods_config.active_view].poll_for_data()
            if buffer_size:
                zones_occupied, raw_occupancy_grid = ods_streams[
                    ods_config.active_view
                ].get_zones_and_occupancy_data()
                i_frames += 1

    # Increase contrast in visualization:
    occupancy_grid = raw_occupancy_grid - 51
    # allow visualization to be colorful
    occupancy_grid = cv2.cvtColor(occupancy_grid, cv2.COLOR_GRAY2BGR)
    # make visualization higher resolution
    occupancy_grid = cv2.resize(
        occupancy_grid, np.array(occupancy_grid.shape[:2]) * upscale_factor
    )
    # Add gridlines 1m apart
    for offset in range(-4, 5):
        occupancy_grid[(100 + offset * 20) * upscale_factor, :] += 50
        occupancy_grid[:, (100 + offset * 20) * upscale_factor] += 50
    # Paint zones on visualization
    for zone, zone_occupied, color in list(
        zip(
            [
                ods_config.get_zone_config_dict_from_zone_setting(zone_set)[f"zone{i}"]
                for i in range(3)
            ],
            zones_occupied,
            colors,
        )
    )[::-1]:
        contours = [
            np.array((np.array(zone) * 20 + 100) * upscale_factor, dtype=np.int32)
        ]
        occupancy_grid = cv2.drawContours(
            occupancy_grid, contours, 0, color[zone_occupied], 1
        )
    # Paint vehicle on visualization
    vehicle_extent = vehicles[vehicle_i]
    if "extent" in vehicle_extent:
        interp_extent_loop = vehicle_extent["extent"].copy()
        interp_extent_loop += [interp_extent_loop[0]]
        # print(interp_extent_loop)
        contours = [
            np.array(
                (np.array(interp_extent_loop) * 20 + 100) * upscale_factor,
                dtype=np.int32,
            )
        ]
        occupancy_grid = cv2.drawContours(
            occupancy_grid, contours, 0, (255, 255, 255), 1
        )
    # Rotate and flip occupancy grid to feel right for desktop testing
    occupancy_grid = cv2.rotate((occupancy_grid), cv2.ROTATE_90_COUNTERCLOCKWISE)
    occupancy_grid = cv2.flip((occupancy_grid), 1)

    # Overlay text
    top_left_text = []
    top_left_text += [f"View ('V')= '{ods_config.active_view}'"]
    top_left_text += [f"Vehicle ('F')= '{vehicles[vehicle_i]['vehicle_name']}'"]
    top_left_text += [f"Zone mode ('Z')= '{zone_modes[zone_mode]}'"]
    top_left_text += [f"Zones occupied= {zones_occupied}"]
    if zone_modes[zone_mode] == "generated":
        top_left_text += [f"  Zone depth ('W'/'S')= {np.round(depth,2)}m"]
        top_left_text += [f"  Added width ('A','D')= {np.round(safety_margin,2)}m"]
        top_left_text += [f"  Zone height = {np.round(height,2)}m"]
    elif zone_modes[zone_mode] == "configured":
        top_left_text += [f"Zone set id ('N')= {zone_set_ids[zone_set_id_i]}"]
    occupancy_grid_with_text = occupancy_grid
    for line_i, text_overlay_line in enumerate(top_left_text):
        occupancy_grid_with_text = cv2.putText(
            occupancy_grid_with_text,
            text_overlay_line,
            org=np.array(org, np.int16)
            + np.array((0, pixels_per_row_of_text)) * (line_i),
            fontFace=font,
            fontScale=fontScale,  # *buffer_data.shape[0]/300,
            color=text_color,
            thickness=int(thickness),  # *buffer_data.shape[0]/300),
        )
    try:
        diagnostic_msgs = O3RDiagnostic(o3r).get_filtered_diagnostic_msgs()
    except Exception as e:
        diagnostic_msgs = [{"name": f"Error encountered while collecting diags {e}"}]
    bottom_left_text = [f"{len(diagnostic_msgs)} active diagnostic messages:"]
    bottom_left_text += [f"  {msg['name']}" for msg in diagnostic_msgs]
    for line_i, text_overlay_line in enumerate(bottom_left_text[::-1]):
        occupancy_grid_with_text = cv2.putText(
            occupancy_grid_with_text,
            text_overlay_line,
            org=np.array((10, 200 * upscale_factor - 10), np.int16)
            + np.array((0, -pixels_per_row_of_text)) * (line_i),
            fontFace=font,
            fontScale=fontScale,  # *buffer_data.shape[0]/300,
            color=text_color,
            thickness=int(thickness),  # *buffer_data.shape[0]/300),
        )

    # Exit the loop if the window has been closed since last update
    try:
        if not cv2.getWindowProperty(winname, 0) >= 0:
            break
    except:
        break

    # Update window.
    cv2.imshow(winname, occupancy_grid_with_text)
    # Collect keypresses
    k = cv2.waitKey(1) & 0xFF

    # Check for changes to the zone configuration on vpu (once every FRAMES_PER_ZONE_CONFIG_RETRIEVAL_FROM_VPU frames if viz has caught up to ods_data_queue)
    if (
        (online)
        and check_for_changed_vpu_state
        # and buffer_size < 2
        and not (i_frames % FRAMES_PER_ZONE_CONFIG_RETRIEVAL_FROM_VPU)
    ):
        # print(i_frames)
        aquired_config = False
        try:
            latest_config = o3r.get()
            active_app = ods_config.get_active_app()
            if active_app:
                zone_config = latest_config["applications"]["instances"][active_app][
                    "configuration"
                ]
                aquired_config = True
        except Exception as e:
            if "Timeout" in str(e):
                print("no response from VPU while querying zone_config")
        if aquired_config and active_app:
            ods_config.get_active_view(latest_config)
            zoneCoordinates = zone_config["zones"]["zoneCoordinates"]
            zone_set = AdHocZoneSetting(
                maxHeight=zone_config["grid"]["maxHeight"],
                view=ods_config.active_view,
                **{
                    f"zone{i}": coordinates
                    for i, coordinates in enumerate(zoneCoordinates)
                },
            )
            view_i = {view: i for i, view in enumerate(ods_stream_list)}[
                ods_config.active_view
            ]
            # print(zone_set)
    # copy variables before modifying
    last_depth = depth
    last_width = safety_margin
    last_vehicle_i = vehicle_i
    last_height = height

    # Define keypresses that cause adjustment of the zone-set-definition
    if k != 255:  # if no keys are pressed, 255 is returned from cv2.waitkey()
        if k == 27:  # quit - esc
            cv2.destroyAllWindows()
            break
        # adjust depth of zones
        elif k == ord("w"):  # forward - 'w'
            depth += adjustment_rate
        elif k == ord("s"):  # reverse - 's'
            depth -= adjustment_rate
        # adjust width of zones
        elif k == ord("a"):  # narrow  - 'a'
            safety_margin -= adjustment_rate
        elif k == ord("d"):  # widen   - 'd'
            safety_margin += adjustment_rate

        elif k == ord("z"):  # toggle zone mode
            zone_mode = (zone_mode + 1) % len(zone_modes)
        elif k == ord("n"):  # cycle through preconfigured zones
            if zone_modes[zone_mode] == "configured":
                zone_set_id_i = (zone_set_id_i + 1) % len(zone_set_ids)
        elif k == ord("f"):  # toggle vehicle
            vehicle_i = (vehicle_i + 1) % len(vehicles)
            height = vehicles[vehicle_i]["height"]
        elif k == ord("x"):  # toggle whether zones are sent to vpu
            send_zone_config = not send_zone_config
        elif k == ord("r"):  # reset   - 'r'
            depth = starting_depth
            safety_margin = starting_safety_margin
            zone_mode = starting_zone_mode
            zone_set_id_i = starting_configured_zone_set_id_idx
        elif k == ord("v"):  # toggle ods-view
            if online:
                view_i = (view_i + 1) % len(ods_stream_list)
                if send_zone_config:
                    ods_config.change_view(ods_stream_list[view_i])
                # TODO collect active zones for the given view if available, otherwise load current zone set

        # TODO toggle whether or not the demo client should update knowledge of the vpu state (view/zones)

        # Update zone on vpu
        if send_zone_config and online:
            if zone_modes[zone_mode] == "configured":
                ods_config.apply_zone_settings(
                    zone_setting=ZoneSet(index=zone_set_ids[zone_set_id_i])
                )
                zone_set = ods_config.get_zones_LUT()[zone_set_ids[zone_set_id_i]]
                zone_set = ZoneSet(index=zone_set_ids[zone_set_id_i])
                zone_config = ods_config.get_zone_config_dict_from_zone_setting(
                    zone_set
                )
                # update the view_i for the demo visualization to reflect the currently active view
                view_i = {view: i for i, view in enumerate(ods_stream_list)}[
                    zone_config["view"]
                ]
            elif zone_modes[zone_mode] == "generated":
                zone_set = generate_zones(
                    depth,
                    safety_margin,
                    vehicle_extent=vehicles[vehicle_i],
                    view=ods_config.active_view,
                    zone_config_id=2000,
                )
                try:
                    zone_config = ods_config.apply_zone_settings(zone_setting=zone_set)
                except Exception as e:
                    # Check for rejection of zone configuration by VPU
                    if "104011" in str(e) or "parsing" in str(e):
                        print(f"Exception_raised for invalid zones: {e}")
                    else:
                        raise e
                    # restore variables:
                    depth = last_depth
                    safety_margin = last_width
                    vehicle_i = last_vehicle_i
                    height = last_height

    last_frame_collected_time = time.perf_counter()

cv2.destroyAllWindows()

# %% Review diagnostic messages
from pprint import pprint

diags = O3RDiagnostic(o3r)
filter = {"state": "active"}
diags.update_diagnostic(filter=filter)
diagnostic = diags.diagnostic
pprint(diagnostic)
# %% Perform additional analysis of ODS data as needed
...
...
# %%
