#! /usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#


import numpy as np
import h5py

GLOBAL_IDX_CNT = None

from collections import namedtuple
from dataclasses import dataclass


@dataclass
class StreamNamesDesc:
    stream_descriptor: namedtuple
    source_name: str
    stream_name_debug: str
    stream_type: str
    stream_id: int
    stream_idx_debug: int


Stream_Descriptor = namedtuple(
    "Stream_Descriptor",
    "name sensorType pcicPort stream_id format imager port portName serialNumber version",
)
Stream_Descriptor_AD = namedtuple("Stream_Descriptor", "name pcicPort sensorType data_format chunk_ids pcic_output_config")

global_index_dtype = np.dtype([("receive_timestamp",np.int64),
                    # stream id providing new data
                    ("current_stream_id", np.uint16),
                    # pointer to last received data for the stream <current_stream_id> (in stream index domain)
                    ("stream_idx", np.uint64),
                ]
            )
struct_2d = np.dtype(
    [
        # receive timestamp of this frame, monotonic increasing
        ("_data_timestamp", np.int64),
        # stream id providing new data
        ("_receive_timestamp", np.int64),
        # pointer to last received data for the stream <current_stream_id> (in stream index domain)
        ("_global_index", np.uint64),
        ("jpeg", h5py.special_dtype(vlen=np.uint8)),
        ("frameCounter", np.dtype("u4")),
        ("timestamp_ns", np.uint64),
        ("exposureTime", np.float32),
        ("extrinsicOpticToUserTrans", np.dtype("(3,)|f4")),
        ("extrinsicOpticToUserRot", np.dtype("(3,)|f4")),
        ("intrinsicCalibModelID", np.uint32),
        ("intrinsicCalibModelParameters", np.dtype("(32,)|f4")),
        ("invIntrinsicCalibModelID", np.uint32),
        ("invIntrinsicCalibModelParameters", np.dtype("(32,)|f4")),
    ]
)

struct_ods = np.dtype(
    [
        ("_data_timestamp", np.dtype("u8")),
        ("_receive_timestamp", np.dtype("u8")),
        ("_global_index", np.dtype("u8")),
        ("timestamp_ns", np.dtype("(3,)|u8")),
        ("width", np.dtype("u4")),
        ("height", np.dtype("u4")),
        ("transformCellCenterToUser", np.dtype("(2,3)|f4")),
        ("image", np.dtype("(200,200)|u1")),
        ("zoneOccupied", np.dtype("(3,)|u1")),
        ("zoneConfigID", np.dtype("u4")),
    ]
)


struct_3d_38k = np.dtype(
    [
        ("_data_timestamp", np.dtype("u8")),
        ("_receive_timestamp", np.dtype("u8")),
        ("_global_index", np.dtype("u8")),
        ("width", np.dtype("u2")),
        ("height", np.dtype("u2")),
        ("frameCounter", np.dtype("u4")),
        ("distance", np.dtype("(172,224)|u2")),
        ("distanceNoise", np.dtype("(172,224)|u2")),
        ("distanceResolution", np.dtype("f4")),
        ("amplitude", np.dtype("(172,224)|u2")),
        ("amplitudeResolution", np.dtype("f4")),
        ("ampNormalizationFactors", np.dtype("(3,)|f4")),
        ("timestamp_ns", np.dtype("(3,)|u8")),
        ("exposureTime", np.dtype("(3,)|f4")),
        ("confidence", np.dtype("(172,224)|u2")),
        ("reflectivity", np.dtype("(172,224)|u1")),
        ("extrinsicOpticToUserTrans", np.dtype("(3,)|f4")),
        ("extrinsicOpticToUserRot", np.dtype("(3,)|f4")),
        ("intrinsicCalibModelID", np.dtype("u4")),
        ("intrinsicCalibModelParameters", np.dtype("(32,)|f4")),
        ("invIntrinsicCalibModelID", np.dtype("u4")),
        ("invIntrinsicCalibModelParameters", np.dtype("(32,)|f4")),
    ]
)

structs_3d_vga = np.dtype(
    [
        ("_data_timestamp", np.dtype("u8")),
        ("_receive_timestamp", np.dtype("u8")),
        ("_global_index", np.dtype("u8")),
        ("width", np.dtype("u2")),
        ("height", np.dtype("u2")),
        ("frameCounter", np.dtype("u4")),
        ("distance", np.dtype("(480,640)|u2")),
        ("distanceNoise", np.dtype("(480,640)|u2")),
        ("distanceResolution", np.dtype("f4")),
        ("amplitude", np.dtype("(480,640)|u2")),
        ("amplitudeResolution", np.dtype("f4")),
        ("ampNormalizationFactors", np.dtype("(3,)|f4")),
        ("timestamp_ns", np.dtype("(3,)|u8")),
        ("exposureTime", np.dtype("(3,)|f4")),
        ("confidence", np.dtype("(480,640)|u2")),
        ("reflectivity", np.dtype("(480,640)|u1")),
        ("extrinsicOpticToUserTrans", np.dtype("(3,)|f4")),
        ("extrinsicOpticToUserRot", np.dtype("(3,)|f4")),
        ("intrinsicCalibModelID", np.dtype("u4")),
        ("intrinsicCalibModelParameters", np.dtype("(32,)|f4")),
        ("invIntrinsicCalibModelID", np.dtype("u4")),
        ("invIntrinsicCalibModelParameters", np.dtype("(32,)|f4")),
    ]
)

global_index_dtype = np.dtype(
    [
        ("receive_timestamp", np.int64),
        # receive timestamp of this frame, monotonic increasing
        ("current_stream_id", np.uint16),
        # stream id providing new data
        ("stream_idx", np.uint64),
    ]
)
# pointer to last received data for the stream <current_stream_id> (in stream index domain)


structs_3d_tof = np.dtype(
    [
        ("_data_timestamp", np.dtype("int64")),
        ("_receive_timestamp", np.dtype("u8")),
        ("_global_index", np.dtype("uint64")),
        ("width", np.dtype("uint16")),
        ("height", np.dtype("uint16")),
        ("frameCounter", np.dtype("uint32")),
        ("distance", np.dtype(("u2", (172, 224)))),
        ("distanceNoise", np.dtype(("u2", (172, 224)))),
        ("amplitude", np.dtype(("u2", (172, 224)))),
        ("confidence", np.dtype(("u2", (172, 224)))),
        ("reflectivity", np.dtype(("u1", (172, 224)))),
        ("distanceResolution", np.dtype("f4")),
        ("amplitudeResolution", np.dtype("f4")),
        ("ampNormalizationFactors", np.dtype(("f4", (3,)))),
        ("extrinsicOpticToUserTrans", np.dtype(("f4", (3,)))),
        ("extrinsicOpticToUserRot", np.dtype(("f4", (3,)))),
        ("intrinsicCalibModelID", np.dtype("uint32")),
        ("intrinsicCalibModelParameters", np.dtype(("f4", (32,)))),
        ("invIntrinsicCalibModelID", np.dtype("uint32")),
        ("invIntrinsicCalibModelParameters", np.dtype(("f4", (32,)))),
        ("timestamp_ns", np.dtype(("<u8", (3,)))),
        ("exposureTime", np.dtype(("f4", (3,)))),
        ("IlluTemperature", np.dtype("f4")),
        ("Mode", np.dtype("(32,)|u2")),
        ("Imager", np.dtype("(32,)|u2")),
        ("measurementBlockIndex", np.dtype("uint32")),
        ("measurementRangeMin", np.dtype("f4")),
        ("measurementRangeMax", np.dtype("f4")),
    ]
)

o3r_json = np.dtype(
    [
        ("_data_timestamp", np.dtype("i8")),
        ("_receive_timestamp", np.dtype("i8")),
        ("_global_index", np.dtype("i8")),
        ("data", h5py.vlen_dtype(np.dtype(np.uint8))),
    ]
)

o3r_diagnostics = np.dtype(
    [
        ("_data_timestamp", np.dtype("i8")),
        ("_receive_timestamp", np.dtype("i8")),
        ("_global_index", np.dtype("i8")),
        ("data", h5py.vlen_dtype(np.dtype(np.uint8))),
    ]
)