# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#

import argparse
import datetime
import logging
from re import S
import socket
from threading import Thread
import time
from queue import Queue
from Receiver import ADReceiver, ConnectionLost, TimeoutTransport
from ifmhdf5_format import IfmHdf5Writer
from collections import namedtuple

from xmlrpc.client import ServerProxy
import json

logger = logging.getLogger(__name__)


def record(filename=None, numberOfSeconds=None, sources=["port2"], ip="192.168.0.69", timeout=3.0, noProgressBar = False,
           autostart=False, appAutoSource=True, forceDisableMotionCompensation=False, useIfm3d=False, closeConnectionOnTimeout=False, iVA=False):
    """
    Record the given sources for the given number of seconds or until CTRL-C is pressed into the given file.
    ATM, 2D ports are not supported.

    :param filename: if None, automatically create a file based on the current date and time.
    :param numberOfSeconds: if None, record for infinite time
    :param sources: a list of the sources (i.e. port[0-6], app[0-9])
    :param ip: IP Address of the VPU
    :param timeout: Timeout in seconds
    :param noProgressBar: Whether to print a progressbar to stdout
    :return:
    """
    if filename is None:
        filename = datetime.datetime.now().strftime("O3R_AD_%Y%m%d_%H%M%S.h5")
    
    if len(set(sources)) != len(sources):
        raise RuntimeError("duplicates sources given.")

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

            if not noProgressBar and not overallNumFrames%10:
                msg =' Number of frames: ' + ' '.join([f'{src}: {numFrames[src]}' for src in final_sources])
                print(f'{msg}', end='\r', flush=True)

    except KeyboardInterrupt:
        if not noProgressBar:
            print()
        logger.info("Keyboard interrupt by user.")
    finally:
        t1 = time.monotonic_ns()
        if not noProgressBar:
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", help="ip address of VPU", default="192.168.0.69")
    parser.add_argument("--timeout", help="timeout to be used in the get function", default=3.0, type=float)
    parser.add_argument("--numSeconds", help="number of seconds to be recorded (default: record until CTRL-C)", default=None, type=int)
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--filename", help="target filename. If not given, a file will be created in the current directory. Pass 'null' for not creating a h5 file.", default=None)
    parser.add_argument("--noProgressBar", "-n", help='Don\'t show progessbar during recording', action='store_true')
    parser.add_argument("--autostart", help='Automatically put the given sources into "RUN" state before recording', action='store_true')
    parser.add_argument("--noAppAutoSource", help="Disable automatism which selects the dependent port of recorded applications", action="store_true")
    parser.add_argument("--forceDisableMotionCompensation", help="Force disabling motion compensation during recording.", action="store_true")
    parser.add_argument("--useIfm3d", help="Use ifm3d library to receive data instead of the pure python implementation. Requires an installed version of ifm3dpy.", action="store_true")
    parser.add_argument("--iva", help="Record the data such that it can be replayed in ifmVisionAssistant.", action="store_true")
    parser.add_argument("--closeConnectionOnTimeout", action="store_true", help="Close connections on timeout (default: false)")
    parser.add_argument("sources", help="Sources can be either port[0-6] or app[0-9].", default=["port0"], nargs="*")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    record(ip=args.ip, timeout=args.timeout, numberOfSeconds=args.numSeconds, filename=args.filename,
           sources=args.sources, noProgressBar=args.noProgressBar, autostart=args.autostart,
           appAutoSource=not args.noAppAutoSource, forceDisableMotionCompensation=args.forceDisableMotionCompensation,
           useIfm3d=args.useIfm3d, iVA=args.iva, closeConnectionOnTimeout=args.closeConnectionOnTimeout)

if __name__ == "__main__":
    main()
