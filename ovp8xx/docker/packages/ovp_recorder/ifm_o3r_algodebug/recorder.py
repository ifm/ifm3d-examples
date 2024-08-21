# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#

import datetime
import logging
import socket
from threading import Thread, Event
import time
from queue import Queue
from collections import namedtuple
import json

from Receiver import ADReceiver, TimeoutTransport
from ifmhdf5_format import IfmHdf5Writer

from xmlrpc.client import ServerProxy

logger = logging.getLogger(__name__)


def record(
        sources:str = "port2",
        filename:str=None,
        numberOfSeconds:float=30,
        ip:str="192.168.0.69",
        timeout: float=3.0,
        ProgressBar: bool = False,
        autostart: bool = True,
        appAutoSource: bool = True,
        forceDisableMotionCompensation: bool =False,
        useIfm3d: bool=True,
        closeConnectionOnTimeout:bool=False,
        iVA:bool=True,
        interrupt: bool = False
        ):


    """
    Record the given sources for the given number of seconds or until CTRL-C is pressed into the given file.
    ATM, 2D ports are not supported.

    :param filename: if None, automatically create a file based on the current date and time.
    :param numberOfSeconds: if <=0, record for infinite time or until interrupted by the user.
    :param sources: a comma-separated of the sources (i.e. port1,port2,app0)
    :param ip: IP Address of the VPU
    :param timeout: Timeout in seconds
    :param noProgressBar: Whether to print a progressbar to stdout
    :param autostart: Whether to automatically start the sources before recording
    :param appAutoSource: Whether to automatically add dependent ports of applications to the sources
    :param forceDisableMotionCompensation: Whether to force disable motion compensation
    :param useIfm3d: Whether to use the ifm3d library to receive data instead of the pure python implementation
    :param closeConnectionOnTimeout: Whether to close connections on timeout
    :param iVA: Whether to record the data such that it can be replayed in ifmVisionAssistant

    """
    if not filename:
        filename = datetime.datetime.now().strftime("O3R_AD_%Y%m%d_%H%M%S.h5")

    sources = sources.split(",")
    sources = [s.strip() for s in sources]
    sources = [s for s in sources if len(s) > 0]
    sources = list(set(sources))

    numberOfSeconds = None if numberOfSeconds < 0.01 else numberOfSeconds

    prx = ServerProxy(uri="http://%s/api/rpc/v1/com.ifm.efector/" % ip, transport=TimeoutTransport(timeout))
    json_config = json.loads(prx.get([""]))

    stream_names = {}
    stream_id = 0
    idx_2d = 0
    idx_3d = 0
    idx_2d_iVA = 0
    idx_3d_iVA = 0
    port6_used = False
    idx_ods = 0
    idx_ods_iVA = 0
    reset_state = []
    set_state = []
    def set_json(tgt, path, value):
        if type(tgt) is list:
            tgt.append({})
            set_json(tgt[-1], path, value)
        elif len(path) > 1:
            if not path[0] in tgt:
                tgt[path[0]] = {}
            set_json(tgt[path[0]], path[1:], value)
        else:
            tgt[path[0]] = value

    Stream_Descriptor = namedtuple('Stream_Descriptor', 'name data_format chunk_ids pcic_output_config')
    Stream_Descriptor_iVA = namedtuple("Stream_Descriptor", "name sensorType pcicPort stream_id data_format imager port serialNumber version")

    keepOrigPortNumbers = False
    if appAutoSource:
        for idx, src in enumerate(sources[:]):
            if src.startswith("app"):
                ports = json_config["applications"]["instances"][src]["ports"]
                classId = json_config["applications"]["instances"][src]["class"]
                if classId == "ods" and "activePorts" in json_config["applications"]["instances"][src]["configuration"]:
                    keepOrigPortNumbers = True
                for p in ports:
                    if not p in sources:
                        logger.info("Adding dependent %s to sources", p)
                        sources.append(p)

    new_sources = sources.copy()

    if iVA:
        for src in sources:
            if src == 'port6': # FixMe: As data receiving on port6 is not yet implemented in ifm3d API
                pass
            else:
                new_sources.append(src+'_iVA')
        
    #################################################################################################
    ### JSON config as a stream required by iVA
    stream_names["o3r_json"] = Stream_Descriptor_iVA("o3r_json", None, None, stream_id, "json", None, None, None, 0)
    stream_id += 1 # Bump stream_id
    
    # Saved JSON data to its stream. Initially False and must be True when started to save data 
    saveJson = False

    final_sources = new_sources.copy()
    for idx, src in enumerate(new_sources):

        iVA_stream_request = any(["iVA" in s for s in src.split("_")])
        if src.startswith("port"):
            temp_src = src.split("_")[0] if iVA_stream_request else src

            if not temp_src in json_config['ports']:
                raise ValueError(f'No device found on {src}')

            sensor_name = json_config['ports'][temp_src]['info']['sensor']
            sensor_type = json_config["ports"][temp_src]["info"]["features"]["type"]
            pcicPort = json_config["ports"][temp_src]["data"]["pcicTCPPort"]
            imager = json_config["ports"][temp_src]["info"]["sensor"]
            port = temp_src[-1]
            serialNumber = json_config["ports"][temp_src]["info"]["serialNumber"]
            version = 0  # TODO
            
            print(f"{idx}: On {src} --> {sensor_name}")

            fwVersion = json_config["device"]["swVersion"]["firmware"]
            if ((fwVersion.startswith("1.0.8-") or fwVersion.startswith("1.0.9-") or fwVersion.startswith("1.0.10-") or forceDisableMotionCompensation)
                    and sensor_name.startswith("IRS2381")
                    and json_config["ports"][temp_src]["processing"]["diParam"]["enableFloorMotionCompensation"]):
                
                print("disabling motion compensation for %s", src)
                if not iVA_stream_request:
                    set_json(set_state, ["ports", temp_src, "processing", "diParam", "enableFloorMotionCompensation"], False)
                    set_json(reset_state, ["ports", temp_src, "processing", "diParam", "enableFloorMotionCompensation"], True)

            if sensor_name == 'OV9782':
                if keepOrigPortNumbers:
                    name = "o3r_2d_" + temp_src[-1]
                    iVA_stream_name = "o3r_rgb_" + temp_src[-1]
                else:
                    name = f"o3r_2d_{idx_2d}"
                    iVA_stream_name = f"o3r_rgb_{idx_2d_iVA}"
                    
                if iVA_stream_request:
                    stream_names[src] = Stream_Descriptor_iVA(iVA_stream_name,
                                                            sensor_type,
                                                            pcicPort,
                                                            stream_id,
                                                            data_format="hdf5-compound-vlen",
                                                            imager=imager,
                                                            port=port,
                                                            serialNumber=serialNumber,
                                                            version=version)
                    idx_2d_iVA += 1
                else:
                    # final_sources.remove(src)
                    stream_names[src] = Stream_Descriptor(f'o3r_2d_{idx_2d}', 'O3Rjpeg', [421, 260], 1)
                    idx_2d += 1
                stream_id += 1
            
            elif sensor_name == "IIM42652":
                if port6_used:
                    raise RuntimeError("cannot record imu twice")
                stream_names[src] = Stream_Descriptor('o3r_imu', "imeas", [], 8)
                stream_id += 1
                port6_used = True
            
            else:
                if keepOrigPortNumbers:
                    name = "o3r_di_" + temp_src[-1]
                    iVA_stream_name = "o3r_tof_" + temp_src[-1]
                else:
                    name = f"o3r_di_{idx_3d}"
                    iVA_stream_name = f"o3r_tof_{idx_3d_iVA}"
                
                if iVA_stream_request:
                    stream_names[src] = Stream_Descriptor_iVA(iVA_stream_name,
                                                            sensor_type,
                                                            pcicPort,
                                                            stream_id,
                                                            data_format="hdf5-compound",
                                                            imager=imager,
                                                            port=port,
                                                            serialNumber=serialNumber,
                                                            version=version,
                                                        )
                    idx_3d_iVA += 1
                else:
                    stream_names[src] = Stream_Descriptor(name, 'imeas', [], 8)
                    idx_3d += 1
                stream_id += 1
                if sensor_name not in ['IRS2381C', 'IRS2877']:
                    print(f'Unknown device "{sensor_name}" on {src} - assuming 3D sensor with AlgoDebug stream')

        elif src.startswith("app"):

            temp_src = src.split("_")[0] if iVA_stream_request else src
            appclass = json_config["applications"]["instances"][temp_src]["class"]

            print(f"{idx}: On {src} --> {appclass}")
            if appclass == "ods":
                if iVA_stream_request:
                    app_pcicPort = json_config["applications"]["instances"][temp_src]["data"]["pcicTCPPort"]
                    stream_names[src] = Stream_Descriptor_iVA(name=f"o3r_app_ods_{idx_ods_iVA}",
                                                            sensorType="app",
                                                            pcicPort=app_pcicPort,
                                                            stream_id=stream_id,
                                                            data_format="hdf5-compound",
                                                            imager=None,
                                                            port=None,
                                                            serialNumber=None,
                                                            version=None,
                                                        )
                    idx_ods_iVA += 1
                else:
                    stream_names[src] = Stream_Descriptor("o3r_ods_%d" % idx_ods, 'imeas', [], 8)
                    idx_ods += 1
                stream_id += 1
                
            else:
                raise RuntimeError("Unknown application class: %s" % appclass)
        else:
            raise RuntimeError("Unknown source: %s" % src)

    if len(set_state) > 0:
        logger.info("Applying changed configuration.")
        for c in set_state:
            prx.set(json.dumps(c))
            time.sleep(1)

    print(f'Filename: {filename}')
    if filename != "null":
        f = IfmHdf5Writer(filename, streamdef=stream_names)
    else:
        f = None

    try:
        rcv = []
        threads = []
        queue = Queue(maxsize=10)
        t0 = time.monotonic_ns()

        def threadFunc(receiver, src):
            receiver.connect()
            try:
                while True:
                    logger.debug("[%s] thread", src)
                    try:
                        data = receiver.get(timeout=timeout)
                        queue.put((src, data), timeout=timeout)
                    except BlockingIOError:
                        continue
                    except socket.timeout:
                        continue
            except Exception as e:
                if receiver.isalive():
                    logger.exception("[%s] Connection to algo debug lost (%s).", src, str(e))
                else:
                    logger.debug("[%s] Connection to algo debug lost (%s) -> already disconnected.", src, str(e))
            finally:
                logger.debug("[%s] thread stopped", src)

        for src in final_sources:
            try:
                pcic_output_config=stream_names[src].pcic_output_config 
                chunk_ids=stream_names[src].chunk_ids
            except AttributeError:
                pcic_output_config = None
                chunk_ids = None
            rcv.append(ADReceiver(ip=ip, source=src, threading=False, xmlrpcTimeout=timeout,
                                  stream_descriptor= stream_names[src],
                                  pcicOutputConf=pcic_output_config, 
                                  chunkIDFilter=chunk_ids,
                                  dataFormat=stream_names[src].data_format,
                                  workaroundForMissingOnceChannels=False,
                                  autostart=autostart,
                                  useIfm3d=True,
                                  closeConnectionOnTimeout=closeConnectionOnTimeout))
            threads.append(Thread(target=threadFunc, args=(rcv[-1], src), daemon=True))
            threads[-1].start()

        numFrames = {src:0 for src in final_sources}
        overallNumFrames = 0
        if numberOfSeconds is None:
            logger.info('Start logging until interrupted to file %s '%filename)
        else:
            logger.info('Start logging for %ds to file %s '%(numberOfSeconds, filename))
        while True:
            src, data = queue.get(timeout=timeout)
            if f is not None:
                if not saveJson:    
                    f.writeStreamJson(stream_name=stream_names["o3r_json"].name, 
                                    buffer=json_config,
                                    data_type=stream_names["o3r_json"].data_format,
                                    data_timestamp_ns= time.time_ns())
                    saveJson = True
                
                if isinstance(data, tuple):
                    f.writeStreamFrame(stream_names[src].name, data[1], data[0], time.time_ns())
                else:
                    f.writeStreamFrame(stream_names[src].name, data, "imeas", time.time_ns())

            numFrames[src] += 1

            logger.debug("%s: wrote frame (%d bytes)", src, len(data))
            overallNumFrames += 1
            if numberOfSeconds is not None and  time.monotonic_ns() - t0 > numberOfSeconds*1e9:
                return

            if ProgressBar and not overallNumFrames%10:
                msg =' Number of frames: ' + ' '.join([f'{src}: {numFrames[src]}' for src in final_sources])
                print(f'{msg}', end='\r', flush=True)
            if type(interrupt) == Event and interrupt.is_set():
                raise KeyboardInterrupt


    except KeyboardInterrupt:
        if ProgressBar:
            print()
        logger.info("Keyboard interrupt by user.")
    finally:
        t1 = time.monotonic_ns()
        if ProgressBar:
            print()
        logger.debug("closing h5 file...")
        if f is not None:
            f.close()
        logger.debug("disconnecting...")
        for i,r in enumerate(rcv):
            logger.debug("disconnecting %s...", new_sources[i])
            r.disconnect()
        logger.debug("joining threads...")
        for i,t in enumerate(threads):
            logger.debug("joining thread %s ...", new_sources[i])
            t.join(timeout=timeout)
            if t.is_alive():
                logger.warning("[%s] joining thread failed (ignored).", new_sources[i])
        
        logger.info("Wrote %d frames to file %s", overallNumFrames, filename)
        for src in final_sources:
            fps = numFrames[src] / (1e-9*(t1-t0))
            logger.info(f' {numFrames[src]} from channel {src}, fps ~ {fps:.1f}')

        if len(reset_state) > 0:
            logger.info("Reverting changed configuration.")
            for c in reset_state:
                prx.set(json.dumps(c))
                time.sleep(1)


if __name__ == "__main__":
    import typer
    typer.run(record)
