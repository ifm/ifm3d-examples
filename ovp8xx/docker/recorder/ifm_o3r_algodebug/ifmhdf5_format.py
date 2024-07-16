# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#

import datetime
import time
import numpy as np
import h5py
from configs import default_structs
from extractFrame import *
from ifm3dpy.device import O3R
import re
class IfmHdf5Writer:
    """
    Class for creating hdf5 files in the format preferred by ifm syntron PCA.
    """

    def __init__(self, filename, streamdef, use_receive_timestamps=True, silent_overwrite=False):
        """
        Creates a new hdf5 file for writing.

        :param filename: the filename given as a string
        :param streamdef: the stream definition, given as a dict mapping stream names (strings) to stream types (strings)
        :param use_receive_timestamps: if true (default) store the receive timestamps in the file. Otherwise use the
                                       data timestamps as receive times.
        """
        type_content = h5py.vlen_dtype(np.dtype(np.uint8))
        type_timestamp = np.int64
        algoDebug_dtype = [('content', type_content),
                 ('_data_timestamp', type_timestamp),
                 ('_receive_timestamp', type_timestamp),
                 ('_global_index', np.uint64)
                ]
        self._name = filename
        if not (self._name.endswith(".h5") or self._name.endswith(".hdf5") or self._name.endswith(".hdf")):
            self._name += ".h5"

        self._useRcvTimestamps = use_receive_timestamps
        # interpolate the name with optionally given variables
        dt = datetime.datetime.now()
        mode = "w" if silent_overwrite else "x"
        
        # create a new HDF5 file / truncate an existing file containing a stream for all existing input ports
        self._currentFile = h5py.File(self._name, mode=mode)

        #########################################################################################################
        ########## Prefill hdf5 file with meta content

        # Write global attributes to the File
        self._currentFile["/"].attrs["name"]            = "ifm_hdf5"
        self._currentFile["/"].attrs["version"]         = np.uint32(1)  # TODO: true versioning
        self._currentFile["/"].attrs["iva_sensortype"]  = "O3R"
        self._currentFile["/"].attrs["description"]     = "This file was created by CLI using a 'O3R' Device written by " + __name__
        
        ts = self.__get_utc_now_time()
        self._currentFile["/"].attrs["creation_date"] = ts[0]

        # Create Index group
        global_index_dtype = np.dtype([("receive_timestamp",np.int64),  # receive timestamp of this frame, monotonic increasing
                                       ("current_stream_id", np.uint16),# stream id providing new data
                                       ("stream_idx", np.uint64)        # pointer to last received data for the stream <current_stream_id> (in stream index domain)
                                       ])


        index_group = self._currentFile.create_group("index")
        streams_in_index = index_group.create_dataset("streams", (len(streamdef),), dtype=h5py.special_dtype(vlen=str))
        timestamps_in_index = index_group.create_group("timestamps")
        globalIndex_in_index = index_group.create_dataset("global_index", (0,), dtype=global_index_dtype,chunks=True,maxshape=(None,),)

        # Create Streams group
        streams = self._currentFile.create_group("streams")

        for sid,sname in enumerate(streamdef):
            name = streamdef[sname].name
            timestamps_in_index.create_dataset(name, (0,), dtype=np.int64, chunks= True, maxshape= (None,))
            streams_in_index[sid] = name
            # For AlgoDebug streams
            if name.startswith('o3r_di') or name.startswith('o3r_2d') or name.startswith('o3r_ods') or name.startswith('o3r_imu'):
                streams.create_dataset(name, (0,), chunks=(1,), maxshape=(None,), dtype=algoDebug_dtype)

            # For O3R JSON stream
            elif name.startswith("o3r_json"):
                streams.create_dataset(name, (0,), dtype=default_structs.o3r_json, chunks=True, maxshape=(None,))
                streams[name].attrs["format"] = streamdef[sname].data_format
            
            # For iVA app stream
            elif name.startswith("o3r_app"):
                print(name)
                streams.create_dataset(name, (0,), dtype=default_structs.struct_ods, chunks=True, maxshape=(None,))
                match = re.search(r'app_ods_(\d+)', name)
                app_index = match.group(1)
                streams[name].attrs["format"] = "hdf5-compound"
                streams[name].attrs["appClass"] = "ods"
                streams[name].attrs["appKey"] = 'app' + app_index # TODO : Fixme
            
            # For iVA 2D stream
            elif name.startswith("o3r_rgb"):
                streams.create_dataset(name, (0,), dtype=default_structs.struct_2d, chunks=True, maxshape=(None,))
                streams[name].attrs["format"]      = streamdef[sname].data_format
                streams[name].attrs["imager"]      = streamdef[sname].imager
                streams[name].attrs["port"]        = streamdef[sname].port
                streams[name].attrs["portType"]    = streamdef[sname].sensorType
                streams[name].attrs["serialNumber"] = streamdef[sname].serialNumber
                streams[name].attrs["version"]     = streamdef[sname].version
            
            # For iVA 3D stream
            else:  # imager streams
                streams.create_dataset(name, (0,), dtype=default_structs.struct_3d_38k, chunks=True, maxshape=(None,))
                streams[name].attrs["format"]      = streamdef[sname].data_format
                streams[name].attrs["imager"]      = streamdef[sname].imager
                streams[name].attrs["port"]        = streamdef[sname].port
                streams[name].attrs["portType"]    = streamdef[sname].sensorType
                streams[name].attrs["serialNumber"] = streamdef[sname].serialNumber
                streams[name].attrs["version"]     = streamdef[sname].version
              
        # setup variables needed during processing
        self._basetime = time.perf_counter_ns()
        self._globalIndex = 0

        # setup flag to save JSON data
        self._jsonSaved = False
    
    def __get_utc_now_time(self):
        utc_now = datetime.datetime.utcnow()
        time_dt = np.dtype(
            [
                ("year", np.int32),
                ("month", np.uint8),
                ("day", np.uint8),
                ("hour", np.uint8),
                ("minute", np.uint8),
                ("second", np.uint8),
                ("microsecond", np.uint32),
            ]
        )
        ts = np.zeros(1, time_dt)
        ts[0]["year"] = utc_now.year
        ts[0]["month"] = utc_now.month
        ts[0]["day"] = utc_now.day
        ts[0]["hour"] = utc_now.hour
        ts[0]["minute"] = utc_now.minute
        ts[0]["second"] = utc_now.second
        ts[0]["microsecond"] = utc_now.microsecond
        return ts

    def checkStreamFormat(self, stream_name, data_type):
        s = self._currentFile["streams"][stream_name]
        if not "format" in s.attrs:
            s.attrs["format"] = data_type
        if s.attrs["format"] != data_type:
            raise RuntimeError("The datatype given for port %s is inconsistent. Received %s, expected %s." %
                               (stream_name, data_type, s.attrs["format"]))
        else:
            return True

    def writeStreamFrame(self, stream_name, buffer, data_type, data_timestamp_ns):
        """
        Writes a frame to the given stream.

        :param stream_name: the name of the stream to be written to (a string instance)
        :param buffer: the buffer to be written (a bytes instance)
        :param data_type: the name of the data type (a string instance)
        :param data_timestamp_ns: the timestamp of the data in [nanoseconds]
        """
        data_timestamp_us = (data_timestamp_ns + 500)//1000
        s = self._currentFile["streams"][stream_name]
        
        self.checkStreamFormat(stream_name, data_type)       
        
        if self._useRcvTimestamps:
            rcvTimestamp = np.int64(time.perf_counter_ns() - self._basetime)//1000
        else:
            rcvTimestamp = data_timestamp_us

        # append the new data to the existing HDF5 dataset
            
        ## To handle 2D stream for iVA
        if data_type == "hdf5-compound-vlen":
                if isinstance(buffer,dict):
                    data_2d = extract_2d_frame(buffer=buffer, global_idx=self._globalIndex, receive_timestamp=rcvTimestamp)
                    self.write_iVA_StreamFrame(data=data_2d,
                                               stream_name=stream_name)
                else:
                    raise RuntimeError("Invalid data")
        
        ## To handle 3D stream for iVA
        elif data_type == "hdf5-compound":
            if stream_name.startswith("o3r_app"):
                if isinstance(buffer,dict):
                    data_app = extract_ods_frame(buffer=buffer, global_idx=self._globalIndex, receive_timestamp=rcvTimestamp)
                    self.write_iVA_StreamFrame(data=data_app,
                                               stream_name=stream_name)
                else:
                    raise RuntimeError("Invalid data")
            
            elif stream_name.startswith("o3r_tof"):
                if isinstance(buffer,dict):
                    data_3d = extract_3d_frame(buffer=buffer, global_idx=self._globalIndex, receive_timestamp=rcvTimestamp)
                    self.write_iVA_StreamFrame(data=data_3d,
                                               stream_name=stream_name)
                else:
                    raise RuntimeError("Invalid data")
        
        # To handle AD streams
        else:
            s.resize((s.shape[0]+1,))
            s[-1] = (np.frombuffer(buffer, dtype=np.uint8),
                    np.int64(data_timestamp_us),
                    np.int64(rcvTimestamp),
                    self._globalIndex)
            self._currentFile.flush()
        
        self._globalIndex = self._globalIndex + 1
    
    def writeStreamJson(self, stream_name, buffer, data_type, data_timestamp_ns):

        """
        Write the JSON configuration to a JSON stream used by iVA

        :param stream_name: the name of the stream to be written to (a string instance)
        :param buffer: the buffer to be written (a bytes instance)
        :param data_type: the name of the data type (a string instance)
        :param data_timestamp_ns: the timestamp of the data in [nanoseconds]
        """
        
        logger.debug("Extracting JSON data")
        data_timestamp_us = (data_timestamp_ns + 500) // 1000
        self.checkStreamFormat(stream_name, data_type)

        if self._useRcvTimestamps:
            receive_timestamp = np.int64(time.perf_counter_ns() - self._basetime)//1000
        else:
            receive_timestamp = data_timestamp_us
        data = extract_json_data(json_config=buffer, global_idx=self._globalIndex, receive_timestamp=receive_timestamp)
        
        self.write_iVA_StreamFrame(data=data, stream_name=stream_name)
        self._globalIndex = self._globalIndex + 1
 
    def write_iVA_StreamFrame(self, data, stream_name):
        data_stream = self._currentFile["streams"][stream_name]
        data_stream.resize(data_stream.shape[0] + 1, axis=0)
        data_stream[-1:] = data["struct"]

        index_timestamp_stream = self._currentFile["index"]["timestamps"][stream_name]
        index_timestamp_stream.resize(index_timestamp_stream.shape[0] + 1, axis=0)
        index_timestamp_stream[-1:] = data["timestamp"]

        global_index_stream = self._currentFile["index"]["global_index"]
        global_index_stream.resize(global_index_stream.shape[0] + 1, axis=0)
        global_index_stream[-1:] = data["global_index"]

        self._currentFile.flush()

    def close(self):
        self._currentFile.close()
        self._currentFile = None
