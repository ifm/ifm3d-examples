#! /usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#


import logging
import queue
import socket
import time
from ifm_imeas.imeas_tools import pack_imeas
from ifm_o3r_algodebug.Receiver import ADReceiver, ConnectionLost, PortInfoNotMatching
from nexxT.Qt.QtCore import QThread, QTimer, Qt, QByteArray
from nexxT.Qt.QtGui import QImage
from nexxT.interface import OutputPort, Filter, DataSample, Services
from nexxT.core.Utils import isMainThread

import ctypes as ct
from nexxT.examples.framework.ImageData import numpyToByteArray
import numpy as np
import struct

logger = logging.getLogger(__name__)

class AlgoDebugGrabber(Filter):
    def __init__(self, env):
        super().__init__(False, True, env)
        logger.debug("AlgoDebugGrabber __init__")
        self.adReceiver = None
        self.playing = False
        self._thread = QThread.currentThread()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.waitForNextSample)
        pc = self.propertyCollection()
        pc.defineProperty("IPAdress", "192.168.0.69", "Sensor ip address.")
        pc.defineProperty("EnableThreading", True, "Whether or not to use threading (this option is usually false if the filter runs in its own exclusive thread).")
        pc.defineProperty("Source", "port0", "The object to be monitored (port0-6 or app0-9).", options=dict(enum=["<none>"] + [("port%d" % v) for v in range(7)] + [("app%d" % v) for v in range(10)]))
        pc.defineProperty("Timeout", 0.5, "Timeout to be used for receive function (use -1 for no timeout).", options=dict(min=-1., max=10.))
        pc.defineProperty("RecvBufsize", 4096, "Buffer size used for socket.recv.", options=dict(min=1024, max=65536))
        pc.defineProperty("OnceRepetitionRate", 0, "Repetition rate of once channels, given in frames. 0 means that the once channels are only outputted at the beginning and at recording start.", options=dict(min=0))
        pc.defineProperty("OnceNumFramesAfterRecStart", 5, "Number of frames to output once channels after recording trigger.", options=dict(min=0, max=100))
        pc.defineProperty("AutomaticReconnect", False, "Whether or not the filter shall try to automatically reconnect in the case of exceptions during receive.")
        pc.defineProperty("PCICPort", 0, "The PCIC port number to be used. If > 0, then xmlrpc is disabled, otherwise this setting is ignored.")
        pc.defineProperty("AutoStart", False, "Whether or not to start the port or application automatically when starting grabbing.")
        pc.defineProperty("CloseConnectionOnTimeout", True, "Whether or not to close connection on timeout (an error will be logged in this case).")
        pc.defineProperty("ExpectedSourceItems", 'None', 
                          'The given string will be evaluated to a python dict() and the algo debug will be started only, if the port object matches the given items.'
                          'For example, {"/info/sensor": ["IRS2381C", "IRS2877C"]} will match the 38k and VGA sensors, '
                          '{"/info/features/type": ["3D"], "/info/features/resolution/height":[172], "/info/features/resolution/width":[224]} will match 3D sensors with resolution 172x224.'
                          'An empty dict {} will match any existing port. None will not execute any check (this is the legacy behaviour).')
        self.port = OutputPort(False, "imeas", env)
        self.addStaticPort(self.port)

    def onStart(self):
        assert QThread.currentThread() == self._thread
        if isMainThread():
            logger.warning("Algo debug runs in main thread which is not recommended. Create a new exclusive thread for it.")
        pc = self.propertyCollection()
        self._openConnection()
        self._reconnection = False
        if pc.getProperty("OnceNumFramesAfterRecStart") > 0:
            rec = Services.getService("RecordingControl")
            rec._startRecording.connect(self.manualOnceChannelOutput, Qt.UniqueConnection)
        if self.adReceiver is not None:
            self.timer.start(100)

    def manualOnceChannelOutput(self):
        if self.adReceiver is not None:
            pc = self.propertyCollection()
            nframes = pc.getProperty("OnceNumFramesAfterRecStart")
            logger.info("Outputting once channels for next %d frames", nframes)
            self.adReceiver.outputOnceChannelsInNextFrames(nframes)

    def waitForNextSample(self):
        assert QThread.currentThread() == self._thread
        try:
            if self._reconnection:
                raise ConnectionLost()
            logger.internal("waiting for sample")
            timeout = self.propertyCollection().getProperty("Timeout")
            packet = self.adReceiver.get(timeout=timeout if timeout >= 0 else None)
            timestamp = DataSample.currentTime()
            if isinstance(packet, dict):
                serialized = pack_imeas(packet)
            else:
                serialized = packet
            sample = DataSample(serialized, "imeas", timestamp)
            logger.debug("transmitting sample")
            self.port.transmit(sample)
            logger.internal("done")
        except queue.Empty:
            logger.debug("Timeout occured (queue)")
        except socket.timeout:
            logger.debug("Timeout occured (socket)")
        except ConnectionLost:
            pc = self.propertyCollection()
            if pc.getProperty("AutomaticReconnect"):
                logger.warning("Connection to algo debug lost. Trying to reconnect...")
                logger.debug("Closing connection ...")
                self._closeConnection()
                logger.debug("Opening connection ...")
                time.sleep(0.1)
                try:
                    self._openConnection()
                    self._reconnection = False
                except:
                    logger.exception("reconnect failed - retrying after 1 second")
                    time.sleep(1)
                    self._reconnection = True
                logger.info("reconnected.")
            else:
                logger.warning("Connection to algo debug lost. You won't get any more data from this.")
                self._closeConnection()
            return
        except Exception:
            logger.exception("Unknown exception")
        logger.internal("restarting timer.")
        self.timer.start(0)

    def _openConnection(self):
        if self.adReceiver is not None:
            logger.warning("Expecting adReceiver to be None; closing connection")
            self._closeConnection()
        pc = self.propertyCollection()
        timeout = self.propertyCollection().getProperty("Timeout")
        pcicPort = pc.getProperty("PCICPort")
        if pcicPort == 0:
            pcicPort = None
        source = pc.getProperty("Source")
        if source == "<none>":
            source = None
        logger.debug("Algo debug source: %s", source)
        try:
            expectedSourceItems = eval(pc.getProperty("ExpectedSourceItems"))
        except Exception as e:
            logger.warning("Can't evaluate expected info items (%s) with python eval (%s). Assuming {} instead.", pc.getProperty("expectedSourceItems"), str(e))
            expectedSourceItems = {}

        try:
            self.adReceiver = ADReceiver(
                ip=pc.getProperty("IPAdress"),
                source=source,
                threading=pc.getProperty("EnableThreading"),
                onceRepetitionRate=pc.getProperty("OnceRepetitionRate"),
                xmlrpcTimeout=timeout if timeout >= 0 else None,
                recv_bufsize=pc.getProperty("RecvBufsize"),
                pcicPort=pcicPort,
                workaroundForMissingOnceChannels=False,
                autostart=pc.getProperty("AutoStart"),
                closeConnectionOnTimeout=pc.getProperty("CloseConnectionOnTimeout"),
                expectedInfoItems=expectedSourceItems
            )
            self.adReceiver.connect()
            self.timer.start(100)
        except PortInfoNotMatching:
            self.adReceiver = None
            logger.warning("Algo debug port %s doesn't match expectations - not connected." % source)

    def _closeConnection(self):
        if self.adReceiver is not None:
            self.timer.stop()
            self.adReceiver.disconnect()
            self.adReceiver = None

    def onStop(self):
        assert QThread.currentThread() == self._thread
        self._closeConnection()
        rec = Services.getService("RecordingControl")
        rec._startRecording.disconnect(self.manualOnceChannelOutput)


class O3RjpegGrabber(Filter):
    def __init__(self, env):
        super().__init__(False, False, env)
        self.adReceiver = None
        self.playing = False
        self._thread = QThread.currentThread()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.waitForNextSample)
        pc = self.propertyCollection()
        pc.defineProperty("IPAdress", "192.168.0.69", "Sensor ip address.")
        pc.defineProperty("PortNumber", 0, "The port number to be monitored (0-5).", options=dict(min=0, max=5))
        pc.defineProperty("EnableThreading", False, "Whether or not to use threading (this option is usually false if the filter runs in its own exclusive thread).")
        pc.defineProperty("Timeout", 3.0, "Timeout to be used for receive function (use -1 for no timeout).", options=dict(min=-1., max=10.))
        pc.defineProperty("RecvBufsize", 4096, "Buffer size used for socket.recv.", options=dict(min=1024, max=65536))
        pc.defineProperty("AutomaticReconnect", False, "Whether or not the filter shall try to automatically reconnect in the case of exceptions during receive.")
        pc.defineProperty("AutoStart", False, "Whether or not to start the port or application automatically when starting grabbing.")
        
        self.dataFormat = "O3Rjpeg"
        self.port = OutputPort(False, self.dataFormat, env)
        self.addStaticPort(self.port)

    def onStart(self):
        assert QThread.currentThread() == self._thread
        if isMainThread():
            logger.warning("O3RjpegGrabber runs in main thread which is not recommended. Create a new exclusive thread for it.")
        pc = self.propertyCollection()
        self._openConnection()
        self.timer.start(100)

    def waitForNextSample(self):
        assert QThread.currentThread() == self._thread
        try:
            logger.internal("waiting for sample")
            timeout = self.propertyCollection().getProperty("Timeout")
            data = self.adReceiver.get(timeout=timeout if timeout >= 0 else None)
            timestamp = DataSample.currentTime()
            sample = DataSample(data[1], data[0], timestamp)
            logger.debug("transmitting sample")
            self.port.transmit(sample)
            logger.internal("done")
        except queue.Empty:
            logger.debug("Timeout occured (queue)")
        except socket.timeout:
            logger.debug("Timeout occured (socket)")
        except ConnectionLost:
            pc = self.propertyCollection()
            if pc.getProperty("AutomaticReconnect"):
                logger.warning("Connection to PCIC (2D imager) lost. Trying to reconnect...")
                self._closeConnection()
                time.sleep(0.1)
                self._openConnection()
            else:
                logger.warning("Connection to PCIC (2D imager) lost. You won't get any more data from this.")
                self._closeConnection()
            return
        except Exception:
            logger.exception("Unknown exception")
        logger.internal("restarting timer.")
        self.timer.start(0)

    def _openConnection(self):
        if self.adReceiver is not None:
            logger.warning("Expecting adReceiver to be None; closing connection")
            self._closeConnection()
        pc = self.propertyCollection()
        timeout = self.propertyCollection().getProperty("Timeout")
        self.adReceiver = ADReceiver(
            ip=pc.getProperty("IPAdress"),
            source=f'port{pc.getProperty("PortNumber")}',
            threading=pc.getProperty("EnableThreading"),
            xmlrpcTimeout=timeout if timeout >= 0 else None,
            recv_bufsize=pc.getProperty("RecvBufsize"),
            workaroundForMissingOnceChannels=False,
            autostart=pc.getProperty("AutoStart"),
            pcicOutputConf = 1, chunkIDFilter= [421, 260], dataFormat=self.dataFormat,
        )
        self.adReceiver.connect()
        self.timer.start(100)

    def _closeConnection(self):
        if self.adReceiver is not None:
            self.timer.stop()
            self.adReceiver.disconnect()
            self.adReceiver = None

    def onStop(self):
        assert QThread.currentThread() == self._thread
        self._closeConnection()


class O3R_RGB_Image_Info(ct.Structure):
    _pack_ = 1
    _fields_ = [
        ("version", ct.c_uint32),
        ("frameCounter", ct.c_uint32),
        ("timestamp_ns", ct.c_uint64),
        ("exposureTime", ct.c_float),
        ("extrinsicOpticToUserTrans", ct.c_float*3),
        ("extrinsicOpticToUserRot", ct.c_float*3),
        ("intrinsicCalibModelID", ct.c_uint32),
        ("intrinsicCalibModelParameters", ct.c_float*32),
        ("invIntrinsicCalibModelID", ct.c_uint32),
        ("invIntrinsicCalibModelParameters", ct.c_float*32),
    ]

class O3RjpegConverter(Filter):
    def __init__(self, env):
        super().__init__(False, False, env)
        self.pjpeg = self.addStaticInputPort("O3Rjpeg")
        self.praw = self.addStaticOutputPort("rawImage")
        self.pimeas = self.addStaticOutputPort("imeas")
        self.toTransmit = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.transmitLastSample)

    def onPortDataChanged(self, port):
        sample = port.getData()
        if not self.toTransmit is None:
            logger.debug("Sample discarded")
        self.toTransmit = sample
        self.timer.start(0)

    def transmitLastSample(self):
        sample = self.toTransmit
        if sample is None:
            return
        data = sample.getContent()
        header_version = struct.unpack("<I", data.data()[0:4])[0]
        if header_version != 1:
            logger.error(f'Unsupported O3Rjpeg version {header_version}')

        header = O3R_RGB_Image_Info.from_buffer_copy(data.data())
         
        serialized = pack_imeas({'O3R_RGB_image_info' : header})
        self.pimeas.transmit(DataSample(serialized, "imeas", 0))

        img = QImage()
        if not img.loadFromData(data[ct.sizeof(header):]):
            logger.warning("could not decode data")
            return
        img = img.convertToFormat(QImage.Format_RGB888)
        w = img.width()
        h = img.height()
        d = img.bytesPerLine() // img.width()
        if d*w != img.bytesPerLine():
            logger.warning("not supported: depth and width are unrelated")
            return
        ptr = img.constBits()
        arr = np.array(ptr).reshape((h,w,d))
        if d >= 4:
            arr = arr[...,:3]
        ba = numpyToByteArray(arr)
        sample = DataSample(QByteArray(ba), "example/image", sample.getTimestamp())
        self.praw.transmit(sample)
        self.toTransmit = None


