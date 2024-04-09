#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
import argparse
import time
import logging
import json
import os
from pathlib import Path
import ifm3dpy
from ifm3dpy.device import O3R
from ifm3dpy.device import Error as ifm3dpy_error
from ifm3dpy.swupdater import SWUpdater
from bootup_monitor import BootUpMonitor

logger = logging.getLogger(__name__)
TIMEOUT_MILLIS = 300000


def _get_firmware_version(o3r: O3R) -> tuple:
    try:
        firmware = o3r.get(["/device/swVersion/firmware"])["device"]["swVersion"][
            "firmware"
        ]
    except Exception as err:
        logger.error(err)
        raise err
    logger.debug(f"VPU firmware: {firmware}")
    try:
        major, minor, patch, build_id = firmware.split(".")
        return (major, minor, patch)
    except ValueError as err:
        raise err


def _update_firmware_016_to_10x(o3r: O3R, filename: str) -> None:
    """Update the OVP firmware from 0.16.x to 1.x.x series.
    This update requires a specific process: the update has
    to be performed twice to install the recovery partition.

    :raises RuntimeError: if the device fails to reboot or
                          the update process did not complete.
    """
    logger.info(f"Start FW update with file: {filename}")
    logger.info(
        "The firmware will be updated twice for the 0.16.x to 1.0.x transition."
    )
    sw_updater = SWUpdater(o3r)

    # 1st application of FW update
    logger.info("First flash FW file")
    sw_updater.flash_firmware(filename, timeout_millis=TIMEOUT_MILLIS)

    logger.info("Rebooting to recovery")
    if not sw_updater.wait_for_recovery(120000):
        raise RuntimeError("Device failed to boot into recovery in 2 minutes")

    logger.info("Boot to recovery mode successful")

    # 2nd application of FW update: final flash
    logger.info("Second flash FW file")
    if not sw_updater.flash_firmware(filename, timeout_millis=TIMEOUT_MILLIS):
        _reboot_productive(o3r=o3r)
        logger.info("Request reboot to productive after second FW flash")
        raise RuntimeError("Firmware update failed")
    logger.info("Second FW flash successful")

    if not sw_updater.wait_for_productive(120000):
        raise RuntimeError("Device failed to boot into productive mode in 2 minutes")


def _update_firmware_via_recovery(o3r: O3R, filename: str) -> None:
    logger.info(f"Start FW update with file: {filename}")

    sw_updater = SWUpdater(o3r)
    logger.info("Rebooting the device to recovery mode")
    sw_updater.reboot_to_recovery()

    if not sw_updater.wait_for_recovery(120000):  # Change 60000 to 120000
        raise RuntimeError("Device failed to boot into recovery in 2 minutes")

    logger.info("Boot to recovery mode successful")
    if not sw_updater.flash_firmware(filename, timeout_millis=TIMEOUT_MILLIS):
        logger.info("Firmware update failed. Boot to productive mode")
        _reboot_productive(o3r=o3r)
        logger.info("Reboot to productive system completed")
        raise RuntimeError("Firmware update failed.")

    logger.info("Flashing FW via recovery successful")
    logger.info("Requesting final reboot after FW update")

    _reboot_productive(o3r)
    logger.info("Reboot to productive system completed")


def _reboot_productive(o3r: O3R) -> None:
    sw_updater = SWUpdater(o3r)
    logger.info("reboot to productive system")
    sw_updater.reboot_to_productive()
    sw_updater.wait_for_productive(120000)

def _check_ifm3dpy_version():
    if ifm3dpy.__version__ < "1.3.3":
        raise RuntimeError(
            "ifm3dpy version not compatible. \nUpgrade via pip install -U ifm3dpy"
        )
def _reapply_config(o3r: O3R, config_file: Path) -> None:
    with open(config_file, "r") as f:
        try:
            logger.info("Reapplying pre-update configuration.")
            o3r.set(json.load(f))
        except ifm3dpy_error as e:
            logger.error(f"Failed to apply previous configuration: {e}")
            schema_fp = Path("json_schema.json")
            with open(schema_fp, "w", encoding="utf-8") as f:
                json.dump(o3r.get_schema(), f, ensure_ascii=False, indent=4)
                logger.info(
                    f"Current json schema dumped to: {Path.absolute(schema_fp)}"
                )

            logger.warning(
                f"Check config against json schema: \n{Path.absolute(schema_fp)}"
            )


# %%
def update_fw(filename: str, ip:str) -> None:
    # Check compatibility of ifm3dpy version
    _check_ifm3dpy_version()
    # Check that swu file exists
    if not os.path.exists(filename):
        raise ValueError("Provided swu file does not exist")

    logger.info(f"device IP: {IP}")
    logger.info(f"FW swu file: {filename}")
    logger.info(f"Monitoring of FW update via messages tab here: http://{IP}:8080/")

    o3r = O3R(ip=ip)

    # check FW 0.16.23
    major, minor, patch = _get_firmware_version(o3r)
    logger.info(f"Firmware version before update: {(major, minor, patch)}")
    if int(major) == 0 and any([int(minor) < 16, int(patch) < 23]):
        raise RuntimeError(
            "Update to FW 0.16.23 first before updating to version 1.0.14"
        )

    config_back_fp = Path("config_backup.json")
    with open(config_back_fp, "w", encoding="utf-8") as f:
        json.dump(o3r.get(), f, ensure_ascii=False, indent=4)
        logger.info(f"Current config dumped to: {Path.absolute(config_back_fp)}")

    # update firmware
    logger.info("///////////////////////")
    logger.info("Start FW update process.")
    logger.info("///////////////////////")
    if (int(major), int(minor), int(patch)) == (0, 16, 23):
        logger.info("FW Update 0.16.23 to 1.0.x started")
        _update_firmware_016_to_10x(o3r, filename)
        logger.info("Update process: file transfer completed")
    elif (int(major), int(minor)) >= (1, 0):
        logger.info("FW Update via recovery started")
        _update_firmware_via_recovery(o3r, filename)
        logger.info("Update process: file transfer completed")
    else:
        logger.error("This FW update is not supported")

    # wait for system to be ready
    while True:
        try:
            fw_updated = o3r.get(["/device/swVersion/firmware"])
            if fw_updated:
                time.sleep(20)
                logger.info("VPU fully booted.")
                break
        except ifm3dpy_error:
            logger.info("Awaiting data from VPU.")
            time.sleep(2)

    logger.info("///////////////////////")
    logger.info("Firmware update complete.")
    logger.info("///////////////////////")

    # check firmware version after update

    major, minor, patch = _get_firmware_version(o3r)
    logger.info(f"Firmware version after update: {(major, minor, patch)}")

    # reapply configuration after update
    _reapply_config(o3r=o3r, config_file=config_back_fp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Firmware update helper", description="Update the O3R embedded firmware"
    )
    parser.add_argument("--filename", help="SWU filename in the cwd")
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel, format="%(message)s")
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        log_to_file = config.LOG_TO_FILE

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"


    update_fw(filename="/home/fares/FW's/OVP81X/OVP81x_Firmware_1.4.22.3949.swu", ip=IP)
# %%
