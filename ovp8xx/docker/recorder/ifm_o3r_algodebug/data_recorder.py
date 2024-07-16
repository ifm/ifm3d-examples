#! /usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#

import time
from collections import deque


import logging
from pathlib import Path
import argparse
import datetime

from ifm3dpy.device import O3R


from configs import default_values
from data_receiver import DataReceiver
from data_saver import DataSaver
from data_stream_recorder.receiver import ADReceiver
from file_writer import _H5Writer


from threading import Thread
from queue import Queue

from configs.default_structs import StreamNamesDesc
from configs.default_structs import Stream_Descriptor_2D_3D, Stream_Descriptor_AD

logger = logging.getLogger(__name__)


class DataRecorder:
    def __init__(
        self,
        ip: str,
        timeout: int,
        numSeconds: int,
        filename: str,
        sources: list,
        forceDisableMotionCompensation=False,
        useIfm3d=False
    ) -> None:

        self._ip = ip
        self._timeout = timeout
        self._numberOfSeconds = numSeconds
        self._filename = filename
        self._forceDisableMotionCompensation = forceDisableMotionCompensation
        self._queue = deque(maxlen=default_values.MAX_QUEUE_SIZE)
        self._o3r = O3R(ip=self._ip)
        self._json_config = self._o3r.get([""])
        self._port6_used = False
        self._useIfm3D = useIfm3d
        self._app_ports_available = []
        self.rcv = []
        self.threads = []

        self._idx_2d = 0
        self._idx_2d_AD = 0
        self._idx_3d = 0
        self._idx_3d_AD = 0
        self._idx_ods = 0
        self._idx_ods_AD = 0
        self._stream_id = 0

        self._sources = sources

    def _disable_motion_compensation(self, src, sensor_type):
        fwVersion = self._json_config["device"]["swVersion"]["firmware"]
        src = src.split("_")[0]
        if (
            (
                fwVersion.startswith("1.0.8-")
                or fwVersion.startswith("1.0.9-")
                or fwVersion.startswith("1.0.10-")
                or self._forceDisableMotionCompensation
            )
            and sensor_type == "3D"
            and self._json_config["ports"][src]["processing"]["diParam"][
                "enableFloorMotionCompensation"
            ]
        ):
            logger.info("disabling motion compensation for %s", src)

            self._json_config["ports"][src]["processing"]["diParam"]["enableFloorMotionCompensation"] = False
            self._o3r.set(self._json_config)

    def appAutoSource(self, sources:list):
        for idx, src in enumerate(sources[:]):
            if src.startswith("app"):
                ports = self._json_config["applications"]["instances"][src.split("_")[0]]["ports"]
                if any(["AD" in s for s in src.split("_")]):
                    for p in ports:
                        if not p+"_AD" in sources:
                            p = p + "_AD"
                            logger.info("Adding dependent %s to sources to save Algo-Debug data", p)
                            self._sources.append(p)
                else:
                    for p in ports:
                        if not p in sources:
                            logger.info("Adding dependent %s to sources to save \'di\' data", p)
                            if p != "port6":
                                self._sources.append(p)

    def generate_stream_names(self, sources: list):
        logger.debug("Generating stream names")

        streams = []
        stream_descriptor_json = Stream_Descriptor_2D_3D("o3r_json", None, None, self._stream_id, "json", None, None, None, None, 0)

        streams.append(
            StreamNamesDesc(
                stream_descriptor=stream_descriptor_json,
                stream_name="json",
                stream_name_debug="json",
                stream_type="json",
                stream_id=self._stream_id,
                stream_idx_debug=None
            )
        )
        # bump stream_id by one - "o3r_json" is counted as its own stream
        self._stream_id += 1

        def _get_port_stream_info_from_json(json_config: dict, src: str, debug:bool):
            if debug:
                src = src.split("_")[0]
            try:
                sensor_type = json_config["ports"][src]["info"]["features"]["type"]
                pcicPort = json_config["ports"][src]["data"]["pcicTCPPort"]
                imager = json_config["ports"][src]["info"]["sensor"]
                port = src[-1]
                serialNumber = json_config["ports"][src]["info"]["serialNumber"]
                version = 0  # TODO
                portName = json_config["ports"][src]["info"]["name"]
            except Exception as e:
                logger.exception(e)
                raise e

            return sensor_type, pcicPort, imager, port, serialNumber, version, portName

        def _get_app_stream_info_from_json(src: str):
            app_pcicPort = self._json_config["applications"]["instances"][src]["data"][
                "pcicTCPPort"
            ]
            return app_pcicPort

        def check_port_availability(
            json_config: dict, src: str, ad_stream_request: bool
        ):
            "raises Value Error if src is not available"
            if ad_stream_request:
                src = src.split("_")[0]
                if not src in json_config["ports"]:
                    raise ValueError(f"No device found on {src}")

            elif not src in json_config["ports"]:
                raise ValueError(f"No device found on {src}")

        for src in sources:
            if src.startswith("port"):

                _ad_stream_request = any(["AD" in s for s in src.split("_")])
                check_port_availability(
                    json_config=self._json_config,
                    src=src,
                    ad_stream_request=_ad_stream_request,
                )
                (
                    sensor_type,
                    pcicPort,
                    imager,
                    port,
                    serialNumber,
                    version,
                    portName,
                ) = _get_port_stream_info_from_json(
                    json_config=self._json_config, src=src, debug=_ad_stream_request
                )


                if sensor_type == "2D" and not _ad_stream_request:
                    stream_name_di=f"o3r_rgb_{self._idx_2d}"
                    stream_desc = Stream_Descriptor_2D_3D(
                        stream_name_di,
                        sensor_type,
                        pcicPort,
                        self._stream_id,
                        format="hdf5-compound-vlen",
                        imager=imager,
                        port=port,
                        portName=portName,
                        serialNumber=serialNumber,
                        version=version,
                    )
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug=stream_name_di,
                            stream_type="normal",
                            stream_id=self._stream_id,
                            stream_idx_debug=None
                        )
                    )
                    self._idx_2d += 1
                    self._stream_id += 1

                elif sensor_type == "2D" and _ad_stream_request:
                    stream_name_di = f"o3r_2d_{self._idx_2d_AD}"
                    stream_desc = Stream_Descriptor_AD(
                        stream_name_di, "O3Rjpeg", [421, 260], 1
                    )
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug=stream_name_di,
                            stream_type="debug",
                            stream_id=self._stream_id,
                            stream_idx_debug=0
                        )
                    )

                    self._idx_2d_AD += 1
                    self._stream_id += 1
                    self._ad_requested = True

                elif sensor_type == "3D" and not _ad_stream_request:
                    stream_name_di = f"o3r_tof_{self._idx_3d}"
                    stream_desc = Stream_Descriptor_2D_3D(
                        f"o3r_tof_{self._idx_3d}",
                        sensor_type,
                        pcicPort,
                        self._stream_id,
                        format="hdf5-compound",
                        imager=imager,
                        port=port,
                        portName=portName,
                        serialNumber=serialNumber,
                        version=version,
                    )
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug=stream_name_di,
                            stream_type="normal",
                            stream_id=self._stream_id,
                            stream_idx_debug=None
                        )
                    )
                    self._idx_3d += 1
                    self._stream_id += 1

                elif sensor_type == "3D" and _ad_stream_request:
                    stream_name_di = f"o3r_di_{self._idx_3d_AD}"
                    stream_desc = Stream_Descriptor_AD(
                        stream_name_di, "imeas", [], 8
                    )

                    self._disable_motion_compensation(src, sensor_type)
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug = stream_name_di,
                            stream_type="debug",
                            stream_id=self._stream_id,
                            stream_idx_debug=0
                        )
                    )
                    self._idx_3d_AD += 1
                    self._stream_id += 1
                    self._ad_requested = True

                elif sensor_type == "IMU" and _ad_stream_request:
                    if self._port6_used:
                        raise RuntimeError("cannot record imu twice")
                    stream_desc = Stream_Descriptor_AD("o3r_imu", "imeas", [], 8)
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug = None,   #TODO
                            stream_type="debug",
                            stream_id=self._stream_id,
                            stream_idx_debug=0
                        )
                    )
                    self._port6_used = True
                    self._stream_id += 1
                    self._ad_requested = True

            elif src.startswith("app"):
                try:
                    appclass = self._json_config["applications"]["instances"][
                        src.split("_")[0]
                    ]["class"]
                except KeyError as e:
                    logger.exception(e)
                    key = src.split("_")[0]
                    raise RuntimeError(
                        f"The requested key: {key} is not available as a datastream"
                    )

                if appclass == "ods" and any(["AD" in s for s in src.split("_")]):
                    stream_name_di = "o3r_ods_%d" % self._idx_ods_AD
                    stream_desc = Stream_Descriptor_AD(
                        stream_name_di, "imeas", [], 8
                    )
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug = stream_name_di,
                            stream_type="debug",
                            stream_id=self._stream_id,
                            stream_idx_debug=0
                        )
                    )
                    self._idx_ods_AD += 1
                    self._ad_requested = True

                if appclass == "ods" and all([not "AD" in s for s in src.split("_")]):
                    app_pcicPort = _get_app_stream_info_from_json(src=src)
                    stream_desc = Stream_Descriptor_2D_3D(
                        name=f"o3r_app_ods_{self._idx_ods}",
                        SensorType="app",
                        pcicPort=app_pcicPort,
                        stream_id=self._stream_id,
                        format='o3r_app',
                        imager=None,
                        port=None,
                        portName=src,
                        serialNumber=None,
                        version=None,
                    )
                    streams.append(
                        StreamNamesDesc(
                            stream_descriptor=stream_desc,
                            stream_name=src,
                            stream_name_debug = f"o3r_app_ods_{self._idx_ods}",
                            stream_type="normal",
                            stream_id=self._stream_id,
                            stream_idx_debug=None
                        )
                    )
                    self._idx_ods += 1
                    self._stream_id += 1

            else:
                raise RuntimeError("Unknown source: %s" % src)

        return streams

    def start_data_receiver_normal(self, streams: list):
        data_receiver = DataReceiver(
            o3r=self._o3r,
            buffer=self._queue,
            streams=streams,
            sources=self._sources,
        )
        data_receiver.start()
        logger.info("Started receiver thread")

        return data_receiver

    def start_data_recorder(self):
        data_recorder = DataSaver(
            o3r=self._o3r,
            buffer=self._queue,
            file_name=self._filename,
        )

        data_recorder.start()
        logger.info("Started Data Saving thread")
        return data_recorder

    def start_data_receiver_debug(self, streams: list):
        """iterate over streams and start each instance

        Args:
            streams (list): StreamDescriptor instances
        """
        for stream in streams:
            self._start_one_data_receiver_AD(stream)
        logger.debug("All debug receiver threads started")

    def _start_one_data_receiver_AD(self, stream):

        def threadFunc(receiver:ADReceiver, src:str, stream:StreamNamesDesc):
            receiver.connect()
            logger.debug("Debug receiver connected")
            try:
                while True:
                    logger.debug("[%s] thread", src)
                    data = receiver.get(timeout=default_values.TIMEOUT, block=True)
                    self._queue.append(
                        {
                            "frame": data,
                            "stream_name": None,
                            "stream_name_debug": stream.stream_descriptor.name,
                            "stream_id": stream.stream_id,
                            "stream_idx": stream.stream_idx_debug,
                            "stream_type": "debug",
                        })
                    stream.stream_idx_debug += 1
                    logger.debug("Received AD data")
            except Exception as e:
                if receiver.isalive():
                    logger.exception(
                        "[%s] Connection to algo debug lost (%s).", src, str(e)
                    )
                else:
                    logger.debug(
                        "[%s] Connection to algo debug lost (%s) -> already disconnected.",
                        src,
                        str(e),
                    )
            finally:
                logger.debug("[%s] thread stopped", src)

        self.rcv.append(
            ADReceiver(
                ip=self._ip,
                source=stream.stream_name.split("_")[0],
                threading=False,
                xmlrpcTimeout=default_values.XMLRPCTIMEOUT,
                pcicOutputConf=stream.stream_descriptor.pcic_output_config,
                chunkIDFilter=stream.stream_descriptor.chunk_ids,
                dataFormat=stream.stream_descriptor.data_format,
                workaroundForMissingOnceChannels=False,
                autostart=False,
                useIfm3d=self._useIfm3D,
            )
        )
        src = stream.stream_name.split("_")[0]
        self.threads.append(
            Thread(target=threadFunc, args=(self.rcv[-1], src, stream), daemon=True)
        )
        self.threads[-1].start()
        logger.debug("Debug Receiver thread started")

    def _setup_filepath(self):
        # def _setup_local_filepath():
        #     saving_path = pathlib.Path
        #     saving_dir = saving_path.cwd() / "tmp"
        #     saving_dir.mkdir(parents=True, exist_ok=True)
        #     return saving_dir

        # saving_dir = _setup_local_filepath()
        saving_dir = Path(default_values.DATA_FILEPATH)

        # filename in local dir checks
        if self._filename is not None:
            self._filename = saving_dir / self._filename
        else:
            filename_h5 = datetime.datetime.now().strftime("O3R_%Y%m%d_%H%M%S.h5")
            self._filename = saving_dir / filename_h5
        logger.info(f"H5 filename: {self._filename}")

    def disconnect_debug_receiver(self):
        for r in self.rcv:
            r.disconnect()
        logger.debug("joining threads...")

        for t in self.threads:
            t.join(timeout=default_values.TIMEOUT)
            if t.is_alive():
                logger.warning("Joining thread failed (ignored).")

    def main(self):
        self._setup_filepath()

        self.appAutoSource(self._sources)
        logger.info(f"Recording sources: {self._sources}")

        streams = self.generate_stream_names(sources=self._sources)
        logger.debug(f"Recording stream names: {streams}")

        # empty H5 file: with meta information prefilled
        with _H5Writer(
            filename=self._filename,
            write_index=True,
            streams=streams,
            desc=None,
        ) as _:
            # use context managing and close file
            pass
        logger.debug("Empty H5 file created")

        # Write camera data to dataset
        streams_normal = []
        streams_debug = []

        for stream in streams:
            if stream.stream_type == "debug":
                streams_debug.append(stream)
            elif stream.stream_type == "normal":
                streams_normal.append(stream)

        t0 = time.monotonic_ns()

        # Start receiving the data
        logger.debug("Kick off receiver threads")
        self.start_data_receiver_debug(streams=streams_debug)
        logger.debug("Normal receiver threads started")

        data_receiver = self.start_data_receiver_normal(streams=streams_normal)
        logger.debug("Debug receiver threads started")


        # Start saving the data
        logger.debug("Kick off data saving thread")
        data_recorder = self.start_data_recorder()

        if self._numberOfSeconds is None:
            logger.info("Start recording until interrupted to file %s " % self._filename)
        else:
            logger.info(
                "Start recording for %ds to file %s " % (self._numberOfSeconds, self._filename)
            )
        try:
            while True:
                    if (self._numberOfSeconds is not None and time.monotonic_ns() - t0 > self._numberOfSeconds * 1e9
                    ):
                        return
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt by user.")

        finally:
            t1 = time.monotonic_ns()
            logger.info(f"Recording stopped: recording duration {t1-t0} s")
            logger.debug("disconnecting...")

            # Stop receiving normal data
            data_receiver.stop()
            data_receiver.join()
            logger.info("Normal data receiving stopped")


            # Stop receiving the debug data
            self.disconnect_debug_receiver()
            logger.info("Debug data receiving stopped")

            # Stop saving data
            data_recorder.stop()
            data_recorder.join()
            logger.info("Empty queues and stop saving data")


def _logging_setup(loglevel):
    logging.basicConfig(level=loglevel, format="%(message)s")
    formatter = logging.Formatter(
        fmt="%(asctime)s, %(levelname)-8s | %(filename)-23s:%(lineno)-4s | %(threadName)15s: %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fh = logging.FileHandler(f"O3R_blackbox_recorder_{now}.txt", mode="w")
    fh.setLevel(loglevel)
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--ip", help="ip address of VPU", default="192.168.0.69")
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--timeout",help="timeout to be used in the get function",default=3.0,type=float,)
    parser.add_argument("--numSeconds",help="number of seconds to be recorded (default: record until CTRL-C)",default=None,type=int,)
    parser.add_argument("--filename",help="target filename. If not given, a file will be created in the current directory.",default=None,)
    parser.add_argument("--forceDisableMotionCompensation",help="Force disabling motion compensation during recording.",action="store_true",)
    parser.add_argument("--useIfm3d",help="Use ifm3d library to receive data instead of the pure python implementation. Requires an installed version of ifm3dpy.",action="store_true",)
    parser.add_argument("sources",
        help="Sources can be either port[0-6], app[0-9], port[0-6]_AD, and app[0-9]_AD",
        default=["app0","app0_AD"],
        # choices=[("port%d" % v) for v in range(7)] +
        #         [("app%d" % v) for v in range(10)] +
        #         [("port%d_AD" % v) for v in range(7)] +
        #         [("app%d_AD" % v) for v in range(10)],
        nargs="*",
    )

    args = parser.parse_args()

    _logging_setup(loglevel=args.loglevel)

    # Check there are no duplicate sources
    if len(set(args.sources)) != len(args.sources):
        raise RuntimeError(f"Duplicate sources given: {args.sources}")

    logging.info(f"ip: {args.ip}, number of Seconds: {args.numSeconds}, sources: {args.sources}")

    data_recorder = DataRecorder(
        ip=args.ip,
        timeout=args.timeout,
        numSeconds=args.numSeconds,
        filename=args.filename,
        sources=args.sources,
        forceDisableMotionCompensation=args.forceDisableMotionCompensation,
        useIfm3d=args.useIfm3d
    )
    data_recorder.main()
