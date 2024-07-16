import time

import logging
import json
import numpy as np
from configs import default_structs

from ifm3dpy.framegrabber import Frame
from ifm3dpy.framegrabber import buffer_id
from ifm3dpy.device import O3R
from ifm3dpy.deserialize import RGBInfoV1 as ds_rgb
from ifm3dpy.deserialize import TOFInfoV4 as ds_tof
from ifm3dpy.deserialize import ODSInfoV1 as ds_ods_info
from ifm3dpy.deserialize import ODSOccupancyGridV1 as ds_ods_grid


logger = logging.getLogger(__name__)


def calculate_distance_image(distance_matrix: np.array, distance_resolution: float) -> np.ndarray:
        """divide distance image by distance_resolution factor and cast to unit16

        Args:
            distance_matrix (np.array): distance image in m
            distance_resolution (float): distance image resolution factor

        Returns:
            np.ndarray: factorized distance image
        """
        return np.divide(distance_matrix, distance_resolution).astype("uint16")

def calculate_amplitude_image(amplitude_matrix: np.array, amplitude_resolution: float) -> np.ndarray:
    """divide amplitude image by amplitude_resolution factor and cast to unit16

    Args:
        amplitude_matrix (np.array): amplitude image in m
        amplitude_resolution (float): amplitude image resolution factor

    Returns:
        np.ndarray: factorized amplitude image
    """
    return np.divide(amplitude_matrix, amplitude_resolution).astype("uint16")

def extract_ods_frame(buffer:dict, global_idx:int, receive_timestamp) -> dict:
    """Extract ODS data from ifm3dpy.Framegrabber.Frame
    :param buffer: A dict object with
                        frame (Frame): frame instance
                        stream_id (int): stream id
                        stream_idx (int): stream index
    :param global_idx: A global index of frame
    :param receive_timestamp : Receive timestamp of the data

    Returns:
        dict --> data
    """
    logger.debug("Unpack ODS APP frame")

    # Unpack buffer
    frame =buffer["frame"]
    stream_id = buffer["stream_id"]
    stream_idx = buffer["stream_idx"]

    ods_info_buffer = frame.get_buffer(buffer_id.O3R_ODS_INFO)
    ods_info = ds_ods_info.deserialize(ods_info_buffer)

    ods_occ_grid_buffer = frame.get_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID)
    ods_occ_grid_info = ds_ods_grid.deserialize(ods_occ_grid_buffer)

    logger.debug(f"3D receive_timestamp: {receive_timestamp}")

    struct_ods = np.zeros(1, default_structs.struct_ods)
    struct_ods[0]["_data_timestamp"] = receive_timestamp
    struct_ods[0]["_receive_timestamp"] = receive_timestamp
    struct_ods[0]["_global_index"] = global_idx
    struct_ods[0]["timestamp_ns"] = ods_occ_grid_info.timestamp_ns
    struct_ods[0]["width"] = ods_occ_grid_info.width
    struct_ods[0]["height"] = ods_occ_grid_info.height
    struct_ods[0]["transformCellCenterToUser"] = np.reshape(
        ods_occ_grid_info.transform_cell_center_to_user, (2, 3)
    )
    struct_ods[0]["image"] = ods_occ_grid_info.image
    struct_ods[0]["zoneOccupied"] = ods_info.zone_occupied
    struct_ods[0]["zoneConfigID"] = ods_info.zone_config_id

    global_index = np.zeros(1, default_structs.global_index_dtype)
    global_index[0]["receive_timestamp"] = receive_timestamp
    global_index[0]["current_stream_id"] = stream_id
    global_index[0]["stream_idx"] = stream_idx

    data = {}
    data["struct"] = struct_ods
    data["global_index"] = global_index
    data["timestamp"] = receive_timestamp

    return data

def extract_3d_frame(buffer:dict, global_idx:int, receive_timestamp) -> dict:
    """Extract 3D TOF data from ifm3dpy.Framegrabber.Frame

    :param buffer: A dict object with
                        frame (Frame): frame instance
                        stream_id (int): stream id
                        stream_idx (int): stream index
    :param global_idx: A global index of frame
    :param receive_timestamp : Receive timestamp of the data

    Returns:
        dict --> data
    """
    logger.debug("Unpack 3D TOF frame")

    # Unpack buffer
    frame =buffer["frame"]
    stream_id = buffer["stream_id"]
    stream_idx = buffer["stream_idx"]
    
    data = {}
    tof_info_buffer = frame.get_buffer(buffer_id.TOF_INFO)
    tof_info = ds_tof.deserialize(tof_info_buffer)
    extr_calib = tof_info.extrinsic_optic_to_user
    intr_calib = tof_info.intrinsic_calibration
    inv_intr_calib = tof_info.inverse_intrinsic_calibration

    mode = tof_info.mode

    imager = tof_info.imager
    mode_array = []
    for character in mode:
        mode_array.append(ord(character))
    imager_array = []
    for character in imager:
        imager_array.append(ord(character))

    logger.debug(f"TOF receive_timestamp: {receive_timestamp}")

    struct_3d = np.zeros(1, default_structs.structs_3d_tof)
    struct_3d[0]["_data_timestamp"] = receive_timestamp
    struct_3d[0]["_receive_timestamp"] = receive_timestamp
    struct_3d[0]["_global_index"] = global_idx
    struct_3d[0]["width"] = 224  # TODO
    struct_3d[0]["height"] = 172  # TODO
    struct_3d[0]["frameCounter"] = frame.frame_count()
    struct_3d[0]["distance"] = calculate_distance_image(
        frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE),
        distance_resolution=tof_info.distance_resolution,
    )
    struct_3d[0]["distanceNoise"] = calculate_distance_image(
        frame.get_buffer(buffer_id.RADIAL_DISTANCE_NOISE),
        distance_resolution=tof_info.distance_resolution,
    )
    # struct_3d[0]['amplitude'] = self.calculate_amplitude_image(
    #     frame.get_buffer(buffer_id.NORM_AMPLITUDE_IMAGE),
    #     amplitude_resolution=tof_info.amp_normalization_factors)

    struct_3d[0]["amplitude"] = frame.get_buffer(
        buffer_id.NORM_AMPLITUDE_IMAGE
    )  # TODO: denormalization not required?

    struct_3d[0]["confidence"] = frame.get_buffer(buffer_id.CONFIDENCE_IMAGE)
    struct_3d[0]["reflectivity"] = frame.get_buffer(buffer_id.REFLECTIVITY)
    struct_3d[0]["distanceResolution"] = tof_info.distance_resolution
    struct_3d[0]["amplitudeResolution"] = tof_info.amplitude_resolution
    struct_3d[0]["ampNormalizationFactors"] = tof_info.amp_normalization_factors
    struct_3d[0]["extrinsicOpticToUserTrans"] = [
        extr_calib.trans_x,
        extr_calib.trans_y,
        extr_calib.trans_z,
    ]
    struct_3d[0]["extrinsicOpticToUserRot"] = [
        extr_calib.rot_x,
        extr_calib.rot_y,
        extr_calib.rot_z,
    ]
    struct_3d[0]["intrinsicCalibModelID"] = intr_calib.model_id
    struct_3d[0]["intrinsicCalibModelParameters"] = intr_calib.parameters
    struct_3d[0]["invIntrinsicCalibModelID"] = inv_intr_calib.model_id
    struct_3d[0]["invIntrinsicCalibModelParameters"] = inv_intr_calib.parameters
    struct_3d[0]["timestamp_ns"] = tof_info.exposure_timestamps_ns
    struct_3d[0]["exposureTime"] = tof_info.exposure_times_s
    struct_3d[0]["IlluTemperature"] = tof_info.illu_temperature
    struct_3d[0]["Mode"] = mode_array
    struct_3d[0]["Imager"] = imager_array
    struct_3d[0]["measurementBlockIndex"] = tof_info.measurement_block_index
    struct_3d[0]["measurementRangeMin"] = tof_info.measurement_range_max
    struct_3d[0]["measurementRangeMax"] = tof_info.measurement_range_min

    global_index = np.zeros(1, default_structs.global_index_dtype)
    global_index[0]["receive_timestamp"] = receive_timestamp
    global_index[0]["current_stream_id"] = stream_id
    global_index[0]["stream_idx"] = stream_idx

    data["struct"] = struct_3d
    data["global_index"] = global_index
    data["timestamp"] = receive_timestamp

    return data

def extract_2d_frame(buffer: dict, global_idx:int, receive_timestamp) -> dict:
    """Extract 2D RGB data from ifm3dpy.Framegrabber.Frame

    Args:
        :param buffer: A dict object with
                            frame (Frame): frame instance
                            stream_id (int): stream id
                            stream_idx (int): stream index
        :param global_idx: A global index of frame
        :param receive_timestamp : Receive timestamp of the data

    Returns:
        dict --> data
    """


    logger.debug("Unpack 2D RGB frame")

    # Unpack buffer
    frame =buffer["frame"]
    stream_id = buffer["stream_id"]
    stream_idx = buffer["stream_idx"]
    
    rgb_info_buffer = frame.get_buffer(buffer_id.RGB_INFO)
    rgb_info = ds_rgb.deserialize(rgb_info_buffer)
    extr_calib = rgb_info.extrinsic_optic_to_user
    intr_calib = rgb_info.intrinsic_calibration
    inv_intr_calib = rgb_info.inverse_intrinsic_calibration
    # receive_timestamp = (rgb_info.timestamp_ns + 500) // 1000
    data_timestamp = receive_timestamp
    rgb_image = frame.get_buffer(buffer_id.JPEG_IMAGE)

    struct_2d = np.zeros(1, default_structs.struct_2d)
    struct_2d[0]["_data_timestamp"] = data_timestamp
    struct_2d[0]["_receive_timestamp"] = receive_timestamp
    struct_2d[0]["_global_index"] = global_idx
    struct_2d[0]["frameCounter"] = frame.frame_count()
    struct_2d[0]["timestamp_ns"] = rgb_info.timestamp_ns
    struct_2d[0]["exposureTime"] = rgb_info.exposure_time
    struct_2d[0]["extrinsicOpticToUserTrans"] = [
        extr_calib.trans_x,
        extr_calib.trans_y,
        extr_calib.trans_z,
    ]
    struct_2d[0]["extrinsicOpticToUserRot"] = [
        extr_calib.rot_x,
        extr_calib.rot_y,
        extr_calib.rot_z,
    ]
    struct_2d[0]["intrinsicCalibModelID"] = intr_calib.model_id
    struct_2d[0]["intrinsicCalibModelParameters"] = intr_calib.parameters
    struct_2d[0]["invIntrinsicCalibModelID"] = inv_intr_calib.model_id
    struct_2d[0]["invIntrinsicCalibModelParameters"] = inv_intr_calib.parameters
    struct_2d[0]["jpeg"] = rgb_image.T

    global_index = np.zeros(1, default_structs.global_index_dtype)
    global_index[0]["receive_timestamp"] = receive_timestamp
    global_index[0]["current_stream_id"] = stream_id
    global_index[0]["stream_idx"] = stream_idx

    data = {}
    data["struct"] = struct_2d
    data["global_index"] = global_index
    data["timestamp"] = receive_timestamp

    return data

def extract_json_data(json_config,global_idx,receive_timestamp) -> dict:
    """Extract JSON data from config

    Returns:
        dict: data dict
    """

    # use global start timestamp when kicking of the data retrieval

    str_byte_json = json.dumps(json_config).encode("utf-8")
    struct_array_json = np.frombuffer(str_byte_json, dtype=np.uint8)

    json_struct = np.zeros(1, default_structs.o3r_json)
    json_struct[0]["_data_timestamp"] = receive_timestamp
    json_struct[0]["_receive_timestamp"] = receive_timestamp
    json_struct[0]["_global_index"] = global_idx
    json_struct[0]["data"] = struct_array_json

    global_index = np.zeros(1, default_structs.global_index_dtype)
    global_index[0]["receive_timestamp"] = receive_timestamp
    global_index[0]["current_stream_id"] = 0
    global_index[0]["stream_idx"] = 0

    data = {}
    data["struct"] = json_struct
    data["global_index"] = global_index
    data["timestamp"] = receive_timestamp

    return data