#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##########################
"""
Unified firmware update script for OVP80x and OVP81x hardware.
Automatically detects hardware type and applies appropriate firmware strategy.
"""

import argparse
import json
import logging
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import ifm3dpy
from ifm3dpy.device import O3R
from ifm3dpy.device import Error as ifm3dpy_error
from ifm3dpy.swupdater import SWUpdater

logger = logging.getLogger(__name__)


# Configuration
class Config:
    TIMEOUT_MILLIS = 300000
    BOOTUP_TIMEOUT_DEFAULT = 60
    BOOTUP_WAIT_TIME = 1
    DEFAULT_IP = "192.168.0.69"
    FIRMWARE_FILE_PATH = Path("/path/to/firmware/OVP8xx_Firmware_1.x.x.x.swu")


class HardwareType:
    OVP80X = "OVP80x"
    OVP81X = "OVP81x"


class BootUpMonitor:
    """Monitor VPU boot readiness through `/device/status`."""

    _READY_STATUS = "OPERATE"

    def __init__(self, o3r: O3R, timeout: int = 25, wait_time: float = 0.5) -> None:
        self.o3r, self.timeout, self.wait_time, self._ip = (
            o3r,
            timeout,
            wait_time,
            o3r.ip,
        )
        self.logger = logging.getLogger(__name__)

    def retrieve_boot_diagnostic(self):
        try:
            for error in self.o3r.get_diagnostic_filtered({"state": "active"})[
                "events"
            ]:
                self.logger.warning("Active errors: %s, %s", error["id"], error["name"])
        except Exception as e:
            self.logger.debug(f"Could not retrieve diagnostic info: {e}")

    def _get_device_status(self):
        status = self.o3r.get(["/device/status"])
        if isinstance(status, dict):
            return status.get("device", {}).get("status")
        return status

    def monitor_VPU_bootup(self) -> bool:
        """Check VPU boot readiness by waiting for `/device/status == OPERATE`."""
        start = time.perf_counter()
        last_status = None

        while time.perf_counter() - start < self.timeout:
            try:
                status = self._get_device_status()
            except ifm3dpy_error:
                status = None

            if status:
                if status != last_status:
                    self.logger.info("Current device status: %s", status)
                    last_status = status

                if status == self._READY_STATUS:
                    self.logger.info("VPU fully booted.")
                    self.retrieve_boot_diagnostic()
                    return True

            time.sleep(self.wait_time)

        raise TimeoutError("Process timed out waiting for VPU to boot")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass


class FirmwareCompatibility:
    @staticmethod
    def parse_firmware_version(
        firmware_str: str,
    ) -> Tuple[int, int, int, Optional[str]]:
        """Parse firmware version string into (major, minor, patch, build_id)"""
        version_match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:-(\w+))?", firmware_str)
        if not version_match:
            raise ValueError(f"Invalid firmware version format: {firmware_str}")
        return (
            int(version_match.group(1)),
            int(version_match.group(2)),
            int(version_match.group(3)),
            version_match.group(4),
        )

    @staticmethod
    def is_same_version(current: str, target: str) -> bool:
        """Check if current and target firmware versions are the same"""
        try:
            c_maj, c_min, c_patch, _ = FirmwareCompatibility.parse_firmware_version(
                current
            )
            t_maj, t_min, t_patch, _ = FirmwareCompatibility.parse_firmware_version(
                target
            )
            return (c_maj, c_min, c_patch) == (t_maj, t_min, t_patch)
        except ValueError:
            return False

    @staticmethod
    def is_compatible_with_ovp80x(firmware_version: str) -> bool:
        """OVP80x: 1.4.32, 1.3.x, 1.2.x, 1.1.x and older (not 1.4.30)"""
        try:
            major, minor, patch, _ = FirmwareCompatibility.parse_firmware_version(
                firmware_version
            )
            if major < 1:
                return True
            elif major == 1:
                if minor < 4:
                    return True
                elif minor == 4:
                    return patch == 32
            return False
        except ValueError:
            logger.warning(
                f"Could not determine compatibility for firmware version: {firmware_version}"
            )
            return False

    @staticmethod
    def is_compatible_with_ovp81x(firmware_version: str) -> bool:
        """OVP81x: 1.4.30 and 1.5.x+"""
        try:
            major, minor, patch, _ = FirmwareCompatibility.parse_firmware_version(
                firmware_version
            )
            if major > 1:
                return True
            elif major == 1:
                if minor > 4:
                    return True
                elif minor == 4 and patch == 30:
                    return True
            return False
        except ValueError:
            logger.warning(
                f"Could not determine compatibility for firmware version: {firmware_version}"
            )
            return False


class HardwareDetector:
    @staticmethod
    def detect_hardware_type(o3r: O3R) -> str:
        """Detect hardware type from device configuration"""
        try:
            device_info = o3r.get(["/device/info"])["device"]["info"]
            part_number = device_info.get("partNumber", "")

            logger.debug(f"Detected part number: {part_number}")

            # OVP81x series
            if part_number.startswith("OVP81"):
                return HardwareType.OVP81X
            # OVP80x series (including OVP801, OVP800, etc.)
            elif part_number.startswith("OVP80"):
                return HardwareType.OVP80X
            else:
                logger.warning(
                    f"Unknown part number: {part_number}. Defaulting to OVP80x strategy."
                )
                return HardwareType.OVP80X

        except Exception as e:
            logger.error(f"Failed to detect hardware type: {e}")
            logger.warning("Defaulting to OVP80x strategy.")
            return HardwareType.OVP80X


class FirmwareUpdater:
    """Unified firmware updater with hardware-specific strategies"""

    def __init__(self, ip: str):
        self.ip = ip
        self.device_state = self._detect_device_state()
        logger.info(f"Connecting to the VPU at {ip} ...")

        if self.device_state == "unreachable":
            raise RuntimeError(
                f"Device {ip} is not reachable. Check connection and power."
            )

        # Initialize O3R connection and detect hardware (skip detection if in recovery mode)
        if self.device_state == "recovery":
            self.o3r = None  # Will be initialized when needed
            self.hw_type = HardwareType.OVP81X  # Default strategy for recovery mode
            logger.debug(f"VPU is in recovery mode")
        else:
            self.o3r = O3R(ip=ip)
            self.hw_type = HardwareDetector.detect_hardware_type(self.o3r)
            logger.debug(f"VPU is in {self.device_state} mode")

    def _setup_logging(self, verbose: int = 0) -> None:
        # Add file logging
        os.makedirs("./logs", exist_ok=True)
        file_name = f"FW_update_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

        file_handler = logging.FileHandler(f"./logs/{file_name}")
        file_formatter = logging.Formatter(
            "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    def _suppress_sw_updater_logging(self, func, *args, **kwargs):
        """Suppress verbose logging from SWUpdater using file descriptor redirection"""
        with tempfile.TemporaryFile() as temp_stderr, tempfile.TemporaryFile() as temp_stdout:
            original_stderr_fd, original_stdout_fd = os.dup(2), os.dup(1)
            try:
                os.dup2(temp_stderr.fileno(), 2)
                os.dup2(temp_stdout.fileno(), 1)
                return func(*args, **kwargs)
            finally:
                os.dup2(original_stderr_fd, 2)
                os.dup2(original_stdout_fd, 1)
                os.close(original_stderr_fd)
                os.close(original_stdout_fd)

    def _detect_device_state(self) -> str:
        """Detect current device state: productive, recovery, or unreachable"""
        try:
            sw_updater = SWUpdater(O3R(ip=self.ip))

            # Check productive mode first (timeout 5000ms = 5 seconds)
            if self._suppress_sw_updater_logging(sw_updater.wait_for_productive, 5000):
                return "productive"

            # Check recovery mode (timeout 5000ms = 5 seconds)
            if self._suppress_sw_updater_logging(sw_updater.wait_for_recovery, 5000):
                return "recovery"

            else:
                return "unreachable"

        except Exception as e:
            logger.error(f"Device unreachable: {e}")
            return "unreachable"

    def _recover_from_recovery_mode(self):
        """Attempt to recover device from recovery mode to productive mode"""
        try:
            logger.info("Attempting to boot device to productive mode...")
            sw_updater = SWUpdater(O3R(ip=self.ip))

            # Try to reboot to productive
            self._suppress_sw_updater_logging(sw_updater.reboot_to_productive)

            # Wait for productive mode with timeout
            logger.info("Waiting for device to boot to productive mode...")
            max_attempts = 60  # 5 minutes
            for attempt in range(max_attempts):
                try:
                    time.sleep(5)
                    test_o3r = O3R(ip=self.ip)
                    test_o3r.get(["/device/info"])
                    logger.info("Device successfully recovered to productive mode")
                    return
                except ifm3dpy_error:
                    if attempt % 12 == 0:  # Log every minute
                        logger.info(
                            f"Still waiting for productive mode... ({attempt * 5}s elapsed)"
                        )
                    continue

            raise RuntimeError(
                "Failed to recover device to productive mode within 5 minutes"
            )

        except Exception as e:
            logger.error(f"Failed to recover from recovery mode: {e}")
            raise RuntimeError(
                f"Device is stuck in recovery mode and cannot be recovered automatically.\n"
                f"Manual intervention required:\n"
                f"1. Power cycle the device\n"
                f"2. Or use recovery mode firmware update directly"
            )

    def _get_firmware_version(
        self, log_version: bool = True
    ) -> Tuple[int, int, int, Optional[str]]:
        try:
            firmware_str = str(self.o3r.firmware_version())
            if log_version:
                logger.info(f"Current firmware version: {firmware_str}")
            return FirmwareCompatibility.parse_firmware_version(firmware_str)
        except Exception as e:
            logger.error(f"Failed to get firmware version: {e}")
            raise

    def _extract_firmware_version_from_filename(self, filename: str) -> str:
        # Look for version patterns in filename
        version_patterns = [
            r"(\d+\.\d+\.\d+\.\d+)",  # 1.4.30.4443
            r"(\d+\.\d+\.\d+)",  # 1.4.30
        ]

        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)

        logger.warning(f"Could not extract firmware version from filename: {filename}")
        return ""

    def _validate_firmware_compatibility(self, firmware_file: Path) -> None:
        """Validate firmware compatibility with detected hardware"""
        firmware_version = self._extract_firmware_version_from_filename(
            firmware_file.name
        )

        if not firmware_version:
            logger.warning(
                "Could not determine firmware version from filename. Proceeding with caution."
            )
            return

        # Get current firmware version for upgrade path validation
        current_major, current_minor, current_patch, _ = self._get_firmware_version(
            log_version=False
        )
        (
            target_major,
            target_minor,
            target_patch,
            _,
        ) = FirmwareCompatibility.parse_firmware_version(firmware_version)

        # Check upgrade path requirements (0.16.x <-> 1.x.x must go through 1.0.x)
        self._validate_upgrade_path(
            current_major,
            current_minor,
            current_patch,
            target_major,
            target_minor,
            target_patch,
            firmware_version,
        )

        if self.hw_type == HardwareType.OVP80X:
            if not FirmwareCompatibility.is_compatible_with_ovp80x(firmware_version):
                raise ValueError(
                    f"Firmware to be flashed {firmware_version} is not compatible with {self.hw_type} hardware. "
                    f"Use firmware version 1.4.32 or older."
                )
        elif self.hw_type == HardwareType.OVP81X:
            if not FirmwareCompatibility.is_compatible_with_ovp81x(firmware_version):
                raise ValueError(
                    f"Firmware to be flashed {firmware_version} is not compatible with {self.hw_type} hardware. "
                    f"Use firmware version 1.4.30 or newer."
                )

        logger.info(
            f"Firmware to be flashed {firmware_version} is compatible with {self.hw_type}"
        )

    def _validate_upgrade_path(
        self,
        curr_maj,
        curr_min,
        curr_patch,
        tgt_maj,
        tgt_min,
        tgt_patch,
        firmware_version,
    ):
        """Validate that firmware upgrade path is valid"""
        current_version = f"{curr_maj}.{curr_min}.{curr_patch}"
        target_version = f"{tgt_maj}.{tgt_min}.{tgt_patch}"

        # 0.16.x to 1.x.x (except 1.0.x) - must go through 1.0.x first
        if curr_maj == 0 and curr_min == 16 and tgt_maj == 1 and tgt_min > 0:
            raise ValueError(
                f"Invalid upgrade path: {current_version} -> {target_version}\n"
                f"SOLUTION: You must upgrade through 1.0.x first:\n"
                f"   Step 1: Update from {current_version} to 1.0.14\n"
                f"   Step 2: Update from 1.0.14 to {target_version}\n"
                f"   This is required due to firmware architecture changes."
            )

        # 1.x.x to 0.16.x - DOWNGRADE NOT SUPPORTED
        elif curr_maj == 1 and tgt_maj == 0 and tgt_min == 16:
            raise ValueError(
                f"Downgrade not supported: {current_version} -> {target_version}\n"
                f"IMPORTANT: Downgrading from 1.x.x firmware to 0.16.x is not possible.\n"
                f"ALTERNATIVES:\n"
                f"   - Stay on current firmware version: {current_version}\n"
                f"   - Upgrade to newer 1.x.x versions only\n"
                f"   - Contact support if 0.16.x firmware is absolutely required"
            )

    def _backup_configuration(self) -> Path:
        """Backup current device configuration"""
        config_backup_path = Path("config_backup.json")
        with open(config_backup_path, "w", encoding="utf-8") as f:
            json.dump(self.o3r.get(), f, ensure_ascii=False, indent=4)
        logger.debug("Config backed up")
        return config_backup_path

    def _reapply_config(self, config_file: Path) -> None:
        """Reapply configuration after firmware update"""
        try:
            with open(config_file, "r") as f:
                self.o3r.set(json.load(f))
        except ifm3dpy_error as e:
            # Generate schema file for troubleshooting
            schema_fp = Path("json_schema.json")
            with open(schema_fp, "w", encoding="utf-8") as f:
                json.dump(self.o3r.get_schema(), f, ensure_ascii=False, indent=4)

            # Re-raise with simple error message
            raise RuntimeError(
                f"Configuration restore failed due to schema changes"
            ) from e

    def _wait_for_vpu_ready(self, timeout: int = None) -> bool:
        """Wait for VPU to be fully ready using integrated BootUpMonitor"""
        if timeout is None:
            timeout = Config.BOOTUP_TIMEOUT_DEFAULT
        try:
            # Create O3R connection if not available (recovery mode scenario)
            o3r = self.o3r if self.o3r is not None else O3R(ip=self.ip)

            with BootUpMonitor(
                o3r, timeout=timeout, wait_time=Config.BOOTUP_WAIT_TIME
            ) as bootup_monitor:
                result = bootup_monitor.monitor_VPU_bootup()
                logger.info("System ready")
                return result
        except TimeoutError as e:
            logger.error(f"VPU bootup timeout after {timeout}s: {e}")
            raise
        except Exception as e:
            # Check if device is actually responsive despite monitoring error
            try:
                test_o3r = O3R(ip=self.ip)
                firmware_version = test_o3r.firmware_version()
                logger.warning(
                    f"VPU bootup monitoring failed but device is responsive (FW: {firmware_version})"
                )
                logger.info("System appears ready despite monitoring error")
                return True
            except Exception:
                logger.error(f"VPU bootup error: {e}")
                raise

    def _update_firmware_unified(self, firmware_file: Path) -> None:
        """Unified firmware update strategy for both hardware types"""

        # Get current firmware version
        major, minor, patch, build_id = self._get_firmware_version()

        # OVP80x specific: Check minimum version requirement
        if self.hw_type == HardwareType.OVP80X:
            if int(major) == 0 and any([int(minor) < 16, int(patch) < 23]):
                raise RuntimeError(
                    "Update to FW 0.16.23 first before updating to version 1.0.14 or newer"
                )

        sw_updater = SWUpdater(self.o3r)

        # Handle special case: 0.16.23 to 1.x.x transition (OVP80x only)
        if self.hw_type == HardwareType.OVP80X and (
            int(major),
            int(minor),
            int(patch),
        ) == (0, 16, 23):
            logger.info("0.16.23 to 1.x.x transition (double flash process)")
            self._update_016_to_10x(sw_updater, firmware_file)
        else:
            # Standard update process for both hardware types
            if self.hw_type == HardwareType.OVP80X and (int(major), int(minor)) >= (
                1,
                0,
            ):
                logger.info("Standard 1.x.x update via recovery")
            else:
                logger.info("Standard update via recovery")

            self._update_via_recovery(sw_updater, firmware_file)

    def _update_016_to_10x(self, sw_updater: SWUpdater, firmware_file: Path) -> None:
        """Update from 0.16.23 to 1.x.x - requires double update process"""

        # First update
        logger.info("First flash...")
        sw_updater.flash_firmware(
            str(firmware_file), timeout_millis=Config.TIMEOUT_MILLIS
        )

        logger.debug("Waiting for recovery mode...")
        recovery_result = self._suppress_sw_updater_logging(
            sw_updater.wait_for_recovery, 120000
        )
        if not recovery_result:
            raise RuntimeError("Device failed to boot into recovery in 2 minutes")

        # Second update (final)
        logger.info("Second flash...")
        if not sw_updater.flash_firmware(
            str(firmware_file), timeout_millis=Config.TIMEOUT_MILLIS
        ):
            self._reboot_productive(sw_updater)
            raise RuntimeError("Second firmware update failed")

        logger.info("Booting to productive mode...")
        productive_result = self._suppress_sw_updater_logging(
            sw_updater.wait_for_productive, 120000
        )
        if not productive_result:
            raise RuntimeError(
                "Device failed to boot into productive mode in 2 minutes"
            )

        # Use integrated BootUpMonitor to ensure full system readiness
        logger.info("Verifying complete system bootup...")
        self._wait_for_vpu_ready(timeout=90)

    def _update_via_recovery(self, sw_updater: SWUpdater, firmware_file: Path) -> None:
        """Standard firmware update via recovery mode"""
        logger.info("Rebooting to recovery...")
        self._suppress_sw_updater_logging(sw_updater.reboot_to_recovery)

        logger.debug("Waiting for recovery mode...")
        recovery_result = self._suppress_sw_updater_logging(
            sw_updater.wait_for_recovery, 120000
        )
        if not recovery_result:
            raise RuntimeError("Device failed to boot into recovery in 2 minutes")

        logger.info("Flashing firmware...")
        if not sw_updater.flash_firmware(
            str(firmware_file), timeout_millis=Config.TIMEOUT_MILLIS
        ):
            logger.info("Flash failed. Rebooting to productive...")
            self._reboot_productive(sw_updater)
            raise RuntimeError("Firmware update failed")

        logger.info("Flash successful. Rebooting...")
        self._reboot_productive(sw_updater)

    def _update_from_recovery_mode(self, firmware_file: Path) -> None:
        """Update firmware when device is already in recovery mode"""
        try:
            sw_updater = SWUpdater(O3R(ip=self.ip))

            # Verify we're in recovery mode
            if not self._suppress_sw_updater_logging(
                sw_updater.wait_for_recovery, 10000
            ):
                raise RuntimeError("Device is not in recovery mode")

            logger.info("Flashing firmware...")
            if not sw_updater.flash_firmware(
                str(firmware_file), timeout_millis=Config.TIMEOUT_MILLIS
            ):
                raise RuntimeError("Recovery mode firmware update failed")

            logger.info("Rebooting to productive mode...")
            self._reboot_productive(sw_updater)

        except Exception as e:
            logger.error(f"Recovery mode update failed: {e}")
            raise RuntimeError(
                f"Failed to update firmware in recovery mode.\n"
                f"Device may need manual recovery:\n"
                f"1. Power cycle the device\n"
                f"2. Try the update process again\n"
                f"3. Contact support if issue persists"
            )

    def _reboot_productive(self, sw_updater: SWUpdater) -> None:
        """Reboot device to productive mode and verify complete bootup"""
        self._suppress_sw_updater_logging(sw_updater.reboot_to_productive)

        logger.info("Booting to productive...")
        if not self._suppress_sw_updater_logging(
            sw_updater.wait_for_productive, 120000
        ):
            raise RuntimeError("Device failed to boot into productive mode")

        # Verify complete VPU bootup
        self._wait_for_vpu_ready(timeout=90)

    def update_firmware(self, firmware_file: Path) -> None:
        """Main firmware update method with robust error handling"""
        # Validate file exists
        if not firmware_file.exists():
            raise ValueError(f"Firmware file does not exist: {firmware_file}")

        # Handle recovery scenarios
        if self.device_state == "recovery":
            logger.info("Direct recovery mode update")
            self._update_from_recovery_mode(firmware_file)
            return

        # Normal productive mode update
        self._validate_firmware_compatibility(firmware_file)

        # Check if firmware is already at target version
        firmware_version = self._extract_firmware_version_from_filename(
            firmware_file.name
        )
        if firmware_version:
            current_major, current_minor, current_patch, _ = self._get_firmware_version(
                log_version=False
            )
            current_version = f"{current_major}.{current_minor}.{current_patch}"

            if FirmwareCompatibility.is_same_version(current_version, firmware_version):
                logger.info(
                    f"Device already has target firmware version {firmware_version}"
                )
                logger.info("Firmware update skipped - no update needed")
                return

        config_backup = self._backup_configuration()

        try:
            logger.info("Starting firmware update...")
            start_time = time.time()
            self._update_firmware_unified(firmware_file)

            # Check new firmware version
            major, minor, patch, build_id = self._get_firmware_version(
                log_version=False
            )
            elapsed_time = time.time() - start_time
            logger.info(
                f"Firmware update successful: {major}.{minor}.{patch} ({elapsed_time:.1f}s)"
            )

            # Reapply configuration
            try:
                self._reapply_config(config_backup)
                logger.info("Configuration restored")
            except Exception:
                logger.warning(
                    "Configuration restore failed - firmware update was successful"
                )
                logger.info(
                    "Manual reconfiguration may be needed due to schema changes"
                )
                # Don't re-raise the exception since firmware update was successful

        except Exception as e:
            # Check if this was a firmware update failure or config restore failure
            error_message = str(e)
            is_config_error = "Configuration restore failed" in error_message

            if is_config_error:
                logger.warning(
                    "Configuration restore failed - firmware update was successful"
                )

                # Show current firmware version to confirm update success
                try:
                    major, minor, patch, build_id = self._get_firmware_version(
                        log_version=False
                    )
                    logger.info(f"Current firmware version: {major}.{minor}.{patch}")
                except Exception:
                    pass

                # Don't raise exception for config-only failures
                return

            else:
                # True firmware update failure
                logger.error(f"Firmware update failed: {e}")

                # Show final firmware status on failure
                try:
                    major, minor, patch, build_id = self._get_firmware_version(
                        log_version=False
                    )
                    logger.info(
                        f"Current firmware after failure: {major}.{minor}.{patch}"
                    )
                except Exception:
                    logger.warning("Could not determine current firmware status")

                raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        prog="Unified Firmware Update",
        description="Update O3R firmware with automatic hardware detection and strategy selection",
    )

    # Make firmware-file optional if Config.FIRMWARE_FILE_PATH is set to a real path
    # If it's None or still the default placeholder, firmware-file argument is required
    default_placeholder = Path("/path/to/firmware/OVP8xx_Firmware_1.x.x.x.swu")
    firmware_required = (
        Config.FIRMWARE_FILE_PATH is None
        or Config.FIRMWARE_FILE_PATH == default_placeholder
    )
    parser.add_argument(
        "--firmware-file",
        help="Path to SWU firmware file",
        required=firmware_required,
        type=Path,
        dest="firmware_file",
    )
    parser.add_argument(
        "--ip", help="Device IP address", default=Config.DEFAULT_IP, dest="ip"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase output verbosity",
        action="count",
        default=0,
        dest="verbose",
    )

    args = parser.parse_args()

    # Command line argument takes priority over configuration
    firmware_file = (
        args.firmware_file
        if args.firmware_file is not None
        else Config.FIRMWARE_FILE_PATH
    )
    ip_address = args.ip if args.ip is not None else Config.DEFAULT_IP

    if firmware_file is None:
        parser.error(
            "Firmware file must be specified either in configuration or via --firmware-file argument"
        )

    # Convert to Path object if it's a string
    if isinstance(firmware_file, str):
        firmware_file = Path(firmware_file)

    # Check ifm3dpy version compatibility
    if ifm3dpy.__version__ < "1.4.3":
        raise RuntimeError(
            "ifm3dpy version not compatible. Upgrade via: pip install -U ifm3dpy"
        )

    # Setup basic logging first, before creating FirmwareUpdater
    logging.basicConfig(
        level=logging.INFO - args.verbose * 10,
        format="%(asctime)s [%(levelname)-5.5s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    try:
        # Create updater
        updater = FirmwareUpdater(ip_address)

        # Setup file logging (this will add file handler to existing console handler)
        updater._setup_logging(args.verbose)

        updater.update_firmware(firmware_file)

    except RuntimeError as e:
        # Handle device connection and recovery errors
        logger.critical(f"Device connection error: {e}")
        logger.info("TROUBLESHOOTING STEPS:")
        logger.info("   1. Check device power and network connection")
        logger.info("   2. Verify device IP address is correct")
        logger.info(f"   3. Try: ping {args.ip}")
        logger.info(
            "   4. If device is in recovery mode, script will attempt automatic recovery"
        )

    except Exception as e:
        logger.critical(f"Firmware update failed: {e}")

        # Always show final firmware status, even on failure
        try:
            logger.info("Checking final firmware status...")
            major, minor, patch, build_id = updater._get_firmware_version(
                log_version=False
            )
            logger.info(
                f"Current firmware version after failure: {major}.{minor}.{patch}"
            )
        except Exception as status_error:
            logger.warning(f"Could not retrieve final firmware status: {status_error}")

        # Exit cleanly without showing Python traceback
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()
