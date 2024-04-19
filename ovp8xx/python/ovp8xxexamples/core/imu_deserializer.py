#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

#############################################
# As there is currently no IMU deserializer implemented in
# the ifm3d API, the data has to be unpacked manually.

from dataclasses import dataclass
from typing import List
import struct

DEFAULT_START_STRING = "star"
DEFAULT_STOP_STRING = "stop"
DEFAULT_IMU_SAMPLES = 128


@dataclass
class IMUSample:
    hw_timestamp: int
    timestamp: int
    temperature: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float

    @staticmethod
    def size() -> int:
        return 2 + 8 + 4 * 7

    @staticmethod
    def parse(data: bytearray) -> "IMUSample":
        offset = 0

        hw_timestamp = struct.unpack_from("<H", data, offset)[0]
        offset += 2

        timestamp = struct.unpack_from("<Q", data, offset)[0]
        offset += 8

        temperature = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        accel_x = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        accel_y = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        accel_z = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        gyro_x = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        gyro_y = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        gyro_z = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        return IMUSample(
            hw_timestamp=hw_timestamp,
            timestamp=timestamp,
            temperature=temperature,
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z,
            gyro_x=gyro_x,
            gyro_y=gyro_y,
            gyro_z=gyro_z,
        )


@dataclass
class AlgoExtrinsicCalibration:
    trans_x: float
    trans_y: float
    trans_z: float
    rot_x: float
    rot_y: float
    rot_z: float

    @staticmethod
    def size() -> int:
        return 4 * 6

    @staticmethod
    def parse(data: bytearray) -> "AlgoExtrinsicCalibration":
        offset = 0

        trans_x = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        trans_y = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        trans_z = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        rot_x = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        rot_y = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        rot_z = struct.unpack_from("<f", data, offset)[0]
        offset += 4

        return AlgoExtrinsicCalibration(
            trans_x=trans_x,
            trans_y=trans_y,
            trans_z=trans_z,
            rot_x=rot_x,
            rot_y=rot_y,
            rot_z=rot_z,
        )


@dataclass
class IMUOutput:
    imu_version: int
    imu_samples: List[IMUSample]
    num_samples: int
    extrinsic_imu_to_user: AlgoExtrinsicCalibration
    extrinsic_imu_to_vpu: AlgoExtrinsicCalibration
    imu_fifo_rcv_timestamp: int

    @staticmethod
    def parse(data) -> "IMUOutput":
        data = data.tobytes()
        offset = 0

        imu_version = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        imu_samples = []
        for _ in range(DEFAULT_IMU_SAMPLES):
            sample = IMUSample.parse(data[offset: offset + IMUSample.size()])
            imu_samples.append(sample)
            offset += IMUSample.size()

        num_samples = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        extrinsic_imu_to_user = AlgoExtrinsicCalibration.parse(
            data[offset: offset + AlgoExtrinsicCalibration.size()]
        )
        offset += AlgoExtrinsicCalibration.size()

        extrinsic_imu_to_vpu = AlgoExtrinsicCalibration.parse(
            data[offset: offset + AlgoExtrinsicCalibration.size()]
        )
        offset += AlgoExtrinsicCalibration.size()

        imu_fifo_rcv_timestamp = struct.unpack_from("<Q", data, offset)[0]
        offset += 4

        return IMUOutput(
            imu_version=imu_version,
            imu_samples=imu_samples,
            num_samples=num_samples,
            extrinsic_imu_to_user=extrinsic_imu_to_user,
            extrinsic_imu_to_vpu=extrinsic_imu_to_vpu,
            imu_fifo_rcv_timestamp=imu_fifo_rcv_timestamp,
        )
