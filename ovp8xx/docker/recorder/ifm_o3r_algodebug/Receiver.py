# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#

import ctypes as ct
import errno
import io
import json
import logging
import queue
import threading

import select
import socket
import struct
import time
from threading import Thread
from xmlrpc.client import ServerProxy, Transport
from http.client import HTTPConnection
from configs import default_structs, default_values 
IFM3DPY_AVAILABLE = True
try:
    import ifm3dpy
    ifm3dpy_version = tuple(int(x.split("+")[0]) for x in ifm3dpy.__version__.split(".")[:3])
    if ifm3dpy_version < (1,2,1):
        IFM3DPY_AVAILABLE = False
        # still get some issues with grabbing algo debug over ifm3dpy, change above line to True to try out
except ImportError:
    IFM3DPY_AVAILABLE = False

try:
    from ifm_imeas.imeas_tools import unpack_imeas, MAGIC_FRAME_START, MAGIC_FRAME_END
    IMEAS_AVAILABLE = True
except ImportError:
    IMEAS_AVAILABLE = False
    MAGIC_FRAME_START = 0xffffdeda
    MAGIC_FRAME_END = 0xadedffff

logger = logging.getLogger(__name__)

implementation = "py-orig"
if implementation == "py-orig":
    ADRCV_AVAILABLE = False
    logger.info("algodebug: py-orig implementation")
    class FatalPcicException(Exception):
        pass
elif implementation == "ctypes":
    from ifm_o3r_algodebug import pcicCtypes
    FatalPcicException = pcicCtypes.FatalPcicException
    ADRCV_AVAILABLE = True
    logger.info("algodebug: ctypes implementation")
elif implementation == "py-new":
    from ifm_o3r_algodebug import pcicPython as pcicCtypes
    FatalPcicException = pcicCtypes.FatalPcicException
    ADRCV_AVAILABLE = True
    logger.info("algodebug: py-new implementation")
else:
    raise ImportError()

if False:
    if not hasattr(select, "appliedLog"):
        def _getLogFile():
            import os, re
            pid = os.getpid()
            tid = threading.current_thread().ident
            tname = re.sub('[^0-9a-zA-Z]+', '_', threading.current_thread().name)
            if not hasattr(_getLogFile, "handles"):
                _getLogFile.handles = {}
            if not (pid, tid) in _getLogFile.handles:
                _getLogFile.handles[pid, tid] = open("socketlog_%d_%s_%d.log" % (pid, tname, tid), "w")
            return _getLogFile.handles[pid, tid]


        def log(fn, loggedArgs=None):
            import inspect
            loggedArgIndices = []
            if loggedArgs is not None:
                for a in loggedArgs:
                    if not isinstance(a, tuple):
                        args, *_ = inspect.getfullargspec(fn)
                        a = (args.index(a), a)
                    loggedArgIndices.append(a)
            def inner(*args, **kw):
                f = _getLogFile()
                t = time.perf_counter_ns()
                f.write("%10d.%09d %s" % (t // 1000000000, t % 1000000000, fn.__name__))
                la = []
                for idx, argname in loggedArgIndices:
                    found = False
                    if len(args) > idx:
                        a = args[idx]
                        found = True
                    elif argname in kw:
                        a = kw[idx]
                        found = True
                    if found:
                        la.append(f"{argname}={a}")
                if len(la) > 0:
                    f.write(" ARGS (" + (", ".join(la)) + ")")
                try:
                    res = fn(*args, **kw)
                    f.write(" -> OK\n")
                    return res
                except Exception as e:
                    f.write(" -> EXCEPT " + str(e) + "\n")
                    raise e
            return inner

        def wrapSocket(fn):
            def inner(*args, **kw):
                res = fn(*args, **kw)
                class Wrapped:
                    def __init__(self, orig):
                        self.__orig = orig
                        self.__cache = {}

                    def __getattr__(self, name):
                        if name not in self.__cache:
                            res = getattr(self.__orig, name)
                            if callable(res):
                                args = None
                                if name == "recv_into":
                                    args = [(1, "nbytes"), (2, "flags")]
                                elif name == "settimeout":
                                    args = [(0, "value")]
                                elif name == "setblocking":
                                    args = [(0, "flag")]
                                res = log(res, args)
                            self.__cache[name] = res
                        return self.__cache[name]

                return Wrapped(res)
            return inner

        select.appliedLog = True
        select.select = log(select.select, ["timeout"])
        socket.socket = wrapSocket(socket.socket)

class BaseADReceiver(queue.Queue):
    """
    Class for receiving data from algo debug. This class implements the data part only without
    connection logic.
    """

    class ChannelHeader(ct.Structure):
        """
        Header for transferring (parts of) channels over TCP, see AD_Impl.h for source code.
        """
        _fields_ = [
            ("id", ct.c_uint32),
            ("frameNumber", ct.c_uint32),
            ("channelIdx", ct.c_uint16),
            ("numChannels", ct.c_uint16),
            ("numSplits", ct.c_uint16),
            ("splitIdx", ct.c_uint16),
            ("totalChannelSize", ct.c_uint32),
            ("splitSize", ct.c_uint32),
            ("splitOffset", ct.c_uint32)
        ]

    def __init__(self, autoInterpret=False, maxsize=0, onceRepetitionRate=0):
        """
        Constructor

        :param maxsize: passed to the Queue constructor (0: infinite size)
        :param onceRepetitionRate: repetition rate of once channels (0: only output the once channels on demand)
        """
        super().__init__(maxsize=maxsize)
        self._frames = {}
        self._newInstance = True
        self._onceChannels = []
        self._onceRepetitionRate = onceRepetitionRate
        self._outputOnceChannelsFrames = 0
        if autoInterpret and not IMEAS_AVAILABLE:
            raise RuntimeError("Need ifm_imeas package to interpret algo debug data.")
        self._autoInterpret = autoInterpret

    def pushChannelData(self, data):
        """
        Notifies the receiver about a new buffer from the algo debug instance.
        Eventually puts new output frames to this queue.
        This method is usually called directly from inherited classes.

        :param data: ctype structure of type SendbufArguments (see AD_cstructs.h)
        :return: None
        """
        # parse the buffer into header and payload
        if isinstance(data, ct.Array):
            hdr = ct.cast(data, ct.POINTER(self.ChannelHeader)).contents
        else:
            hdr = self.ChannelHeader.from_buffer_copy(data[:ct.sizeof(self.ChannelHeader)])
        buf = data[ct.sizeof(self.ChannelHeader):]

        if self._newInstance:
            if hdr.channelIdx == 0:
                self._newInstance = False
            else:
                # wait for clean start (this is only necessary because we get the data in async mode)
                return

        assert hdr.splitSize == len(buf)
        assert len(buf) + ct.sizeof(hdr) == len(data)

        if not hdr.frameNumber in self._frames:
            # the frame number is not yet known
            if hdr.splitIdx == 0:
                # split index is zero -> this is the start of the channel
                # add the frame and setup the channels as described in the header
                self._frames[hdr.frameNumber] = {}
                for i in range(hdr.numChannels):
                    self._frames[hdr.frameNumber][i] = [None, False]  # [buffer, completed]
            else:
                # the split idx is non-zero, this means that we do not have the beginning of the frame and therefore
                # we ignore the buffer
                logger.warning("Ignoring frame without history but non-zero split index.")
                return

        f = self._frames[hdr.frameNumber]
        if f[hdr.channelIdx][0] is None:
            # setup the buffer if not already there
            f[hdr.channelIdx][0] = bytearray(hdr.totalChannelSize)

        # fill the buffer with the given data
        f[hdr.channelIdx][0][hdr.splitOffset:hdr.splitOffset + hdr.splitSize] = buf

        if hdr.splitIdx == hdr.numSplits - 1:
            # last part of channel received
            f[hdr.channelIdx][1] = True
            assert hdr.splitOffset + hdr.splitSize == hdr.totalChannelSize
            # put completed frames to the queue
            self.output()

    def outputOnceChannelsInNextFrames(self, numFrames=1):
        self._outputOnceChannelsFrames = numFrames

    def getOnceChannels(self):
        """
        Return once channels as an imeas packet
        :return: a bytes instance suitable for imeas interpretation
        """
        magic_frame_start = struct.pack("<I", MAGIC_FRAME_START)
        magic_frame_end = struct.pack("<I", MAGIC_FRAME_END)
        parts = [magic_frame_start]
        parts.extend(self._onceChannels)
        parts.append(magic_frame_end)
        return b''.join([p for p in parts if p is not None])

    def output(self):
        """
        checks the frames for completion and put completed frames into the queue
        :return: None
        """
        magic_frame_start = struct.pack("<I", MAGIC_FRAME_START)
        magic_frame_end = struct.pack("<I", MAGIC_FRAME_END)
        for fn in sorted(self._frames.keys()):
            f = self._frames[fn]

            if all([f[c][1] for c in f.keys()]):
                # frame complete
                parts = [f[c][0] for c in f.keys()]
                if fn == 0:
                    # once channels are complete
                    self._onceChannels = parts[:]
                parts[0:0] = [magic_frame_start]
                if ((self._onceRepetitionRate > 0 and fn > 0 and fn % self._onceRepetitionRate == 0) or
                        (self._outputOnceChannelsFrames > 0)):
                    self._outputOnceChannelsFrames = max(0, self._outputOnceChannelsFrames - 1)
                    parts.extend(self._onceChannels)
                parts.append(magic_frame_end)
                if self._autoInterpret:
                    r, _ = unpack_imeas(b''.join([p for p in parts if p is not None]), add_toplevel_wrapper=False)
                else:
                    r = b''.join([p for p in parts if p is not None])
                self.put(r)
                del self._frames[fn]
            else:
                logger.debug("not all channels are ready, number of frames in queue: %d, ready=%s", len(self._frames), [f[c][1] for c in f.keys()])
                return

class ConnectionLost(Exception):
    pass

class PortInfoNotMatching(Exception):
    pass

class TimeoutTransport(Transport):
    def __init__(self, timeout):
        self.timeout = timeout
        super().__init__()

    def make_connection(self, host):
        connection = HTTPConnection(host)
        connection.timeout = self.timeout
        self._connection = host, connection
        return connection

class ADReceiver(BaseADReceiver):
    """
    Usage:

    with ADReceiver("192.168.0.69", 0, autoInterpret=True) as rcv:
        while 1:
            frame = rcv.get()
            # process frame
    """
    def __init__(self, ip, source, pcicPort=None,stream_descriptor=None,
                 autoInterpret=False, threading=False, recv_bufsize=4096, onceRepetitionRate=0,
                 xmlrpcTimeout=3.0, xmlrpcPort=None, workaroundForMissingOnceChannels=True, pcicOutputConf = 8,
                 chunkIDFilter=[], dataFormat='imeas', autostart=False, useIfm3d=True, closeConnectionOnTimeout=True,
                 expectedInfoItems=None, useCDLL=ADRCV_AVAILABLE):
        """
        Constructor
        :param ip: ip address of the sensor
        :param source: Must be a string matching port[0-6] or app[0-9]. In case of None, the xmlrpc interface will not be used.
        :param pcicPort: TCP port of the PCIC system (e.g. 50012). 
                         The port might be None in which case an autodetection will be applied.
        :param pcicOutputConf: Output configuration of PCIC (cf. O3R-4960). The default is 8, which translates to 'algo debug only'
        :param chunkIDFilter: List of chunkIDs which shall be put together to one BLOB. The order of the IDs in the list 
                              configures also the order of the chunk payload in the final BLOB. For dataFormat 'imeas', the
                              list can be left empty (default).
        :param dataFormat: Format string which will be added as attribute to the appropriate stream in the H5 file.
        :param autostart: whether or not to automatically put the port/application object in RUN state.
        """
        super().__init__(autoInterpret=autoInterpret, onceRepetitionRate=onceRepetitionRate)
        self._ip = ip

        ####################################################################################
        ## Handling iVA ports for iVA
        self._iVA_stream_request = any(["iVA" in s for s in source.split("_")])
        self._source = source.split("_")[0] if self._iVA_stream_request else source
        self._pcicPortConfigured = pcicPort
        self._pcicPort = None
        self._threading = threading
        self._thread = None
        self._finished = False
        self._recv_bufsize = 10*1024*1024
        self._recvall_state = None
        self._xmlrpcTimeout = xmlrpcTimeout
        self._xmlrpcPort = xmlrpcPort
        self._timebarrier = None
        self._workaroundForMissingOnceChannels = workaroundForMissingOnceChannels
        self._pcicOutputConf = pcicOutputConf
        self._chunkIDFilter = chunkIDFilter
        self._dataFormat = dataFormat
        self._autostart = autostart
        self._closeConnectionOnTimeout = closeConnectionOnTimeout
        self._useCDLL = useCDLL
        if expectedInfoItems is not None:
            prx = self._xmlrpcServerProxy()
            try:
                
                prefix = f"/ports/{self._source}" if self._source.startswith("port") else f"/applications/instances/{self._source}"
                logger.debug("getting %s", prefix)
                config = json.loads(prx.get([prefix]))
                while len(config.keys()) == 1 and list(config.keys())[0] != self._source:
                    config = config[list(config.keys())[0]]
                config = config[self._source]
            except Exception as e:
                logger.debug("AlgoDebug[%s] cannot get port/application object (%s).", self._source, str(e))
                raise PortInfoNotMatching()
            for jsonPtr, expectedValues in expectedInfoItems.items():
                test = config
                for k in jsonPtr.split("/"):
                    if k != "":
                        try:
                            test = test[k]
                        except KeyError as e:
                            logger.debug("AlgoDebug[%s] cannot resolve json pointer %s (%s).", self._source, jsonPtr, str(e))
                            raise PortInfoNotMatching()
                if test not in expectedValues:
                    logger.debug("AlgoDebug[%s] json pointer %s resolved to %s and this is not matching %s", 
                                 self._source, jsonPtr, test, expectedValues)
                    raise PortInfoNotMatching()
        if useIfm3d and not IFM3DPY_AVAILABLE:
            raise RuntimeError("useIfm3d is set to true, but ifm3dpy is not installed in a suitable version.")
        self._useIfm3d = useIfm3d
        if self._useIfm3d:
            # ifm3d always creates a new thread, so it is mandatory to use the threading mode.
            self._threading = True
        if dataFormat not in ["imeas"]:
            self._workaroundForMissingOnceChannels = False

        self._streamIdx = 0
        self._ivaDataFormats = {"hdf5-compound-vlen", "hdf5-compound", "o3r_app"}
        try:
            self._streamId = stream_descriptor.stream_id
        except AttributeError:
            self._streamId = None
        
        self._streamName = stream_descriptor.name

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def threading(self):
        return self._threading

    def get(self, block=True, timeout=None):
        """
        Overwritten from queue.Queue. Note that block=False and timeout parameters are properly supported if and only
        if the receiver is in threading mode. Otherwise, this function might block even if requested otherwise.
        :param args:
        :param kwargs:
        :return:
        """
        self._timebarrier = None
        res = None
        if self._threading:
            if self._finished:
                raise ConnectionLost()
            res = super().get(block=block, timeout=timeout)
        elif not self._useIfm3d:
            if block and timeout is not None:
                if self._useCDLL:
                    self._timebarrier = self._socket.gettime() + int(timeout*1e9)
                else:
                    self._timebarrier = time.monotonic_ns() + int(timeout*1e9)
                self._socket.setblocking(False)
            elif block and timeout is None:
                self._socket.setblocking(True)
            else:
                self._socket.setblocking(False)
            try:
                while self.empty():
                    self._receiveFrame()
            except FatalPcicException:
                logger.exception("Connection lost.")
                raise ConnectionLost()

            res = super().get(block=block, timeout=timeout)
        else:
            # ifm3d
            if block and timeout is None:
                self._timebarrier = None
            elif block and timeout is not None:
                self._timebarrier = time.monotonic_ns() + int(timeout*1e9)
            else:
                self._timebarrier = time.monotonic_ns()
            while self.empty():
                if self._timebarrier is None:
                    [ok, frame] = self._fg.wait_for_frame().wait()
                    if ok:
                        self._on_new_ifm3dpy_frame(frame)
                else:
                    timeout = int(max(0.0, self._timebarrier - time.monotonic_ns())//1e6)
                    [ok, frame] = self._fg.wait_for_frame().wait_for(timeout)
                    if ok:
                        self._on_new_ifm3dpy_frame(frame)
                    if time.monotonic_ns() > self._timebarrier:
                        break
            res = super().get(block=block, timeout=None if self._timebarrier is None else max(0, self._timebarrier - time.monotonic_ns())*1e-9)
        # workaround for missing once channels
        if len(self._onceChannels) == 0 and self._workaroundForMissingOnceChannels:
            logger.warning("apply workaround for missing once channels")
            self._enableAlgoDebug(False)
            time.sleep(0.5)
            self._enableAlgoDebug(True)
            #self.disconnect()
            #self.connect()
        return res

    def _recvall(self, msg_len):
        assert not self._useCDLL
        if self._recvall_state is None:
            self._recvall_state = [bytearray(msg_len), 0]
        max_msg_size = self._recv_bufsize
        view = memoryview(self._recvall_state[0])[self._recvall_state[1]:]
        while self._recvall_state[1] < msg_len:
            nbytes = 0
            try:
                readyRead = None
                timeout = None
                if self._timebarrier is not None:
                    while True:
                        timeout = max(0, 1e-9*(self._timebarrier - time.monotonic_ns()))
                        readyRead, _ , _ = select.select([self._socket], [], [], timeout)
                        if timeout == 0 or len(readyRead) == 1:
                            break
                    if len(readyRead) == 0:
                        raise BlockingIOError()
                try:
                    nbytes = self._socket.recv_into(view, min(msg_len-self._recvall_state[1], max_msg_size))
                except BlockingIOError as ioerr:
                    if (self._timebarrier is None or timeout > 0) and ioerr.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                        continue
                    raise ioerr
                except ConnectionAbortedError as err:
                    logger.debug("ConnectionAbortedError exception during recv_info: buf=%d len=%d, msg_len=%d received=%d readyRead=%s timeout=%s",
                                  len(view), min(msg_len-self._recvall_state[1], max_msg_size), msg_len, self._recvall_state[1], readyRead, timeout)
                    raise err
                view = view[nbytes:]
            except Exception as e:
                if self._finished:
                    logger.debug("Received exception during socket.recv, ignored because AD is finished.")
                elif not self._closeConnectionOnTimeout and isinstance(e, BlockingIOError):
                    raise socket.timeout()
                else:
                    logger.exception("Received exception during socket.recv.")
                raise ConnectionLost()
            if nbytes == 0:
                logger.debug("received 0 bytes -> connection lost")
                raise ConnectionLost()
            self._recvall_state[1] += nbytes
        ret = self._recvall_state[0]
        self._recvall_state = None
        return ret

    def _readChunks(self):
        answer, ticket = self._readAnswer()
        logger.debug("ticket=%s len(ans)=%d", ticket, len(answer))

        metaDataList = []
        chunkDataList = []
        chunkTypeList = []

        if ticket == b"0000" or ticket == b"0020":
            f = io.BytesIO(answer)
            token = f.read(4)
            if token != b"star":
                raise RuntimeError("Unexpected token, expected b'star', got %s" % repr(token))
            while True:
                data = f.read(4)
                # stop if frame finished
                if data == b"stop":
                    break
                chunkType, = struct.unpack("I", data)
                try:
                    # else read rest of image header
                    chunkSize, headerSize, headerVersion, imageWidth, imageHeight, pixelFormat, timestamp, frameCount, \
                        statusCode, timestampSeconds, timestampNano = struct.unpack("IIIIIIIIIII", f.read(44))
                except struct.error:
                    logger.warning("Unexpected error in data stream, stop with this PCIC packet.")
                    break
                metaData = ''
                if headerVersion == 3:
                    # read rest of chunk header
                    metaData = f.read(headerSize - 48)
                    
                chunkData = f.read(chunkSize-headerSize)

                metaDataList.append(metaData)
                chunkDataList.append(chunkData)
                chunkTypeList.append(chunkType)
        else:
            logger.debug("Ignoring ticket %s, length=%d", ticket, len(answer))

        return chunkTypeList, chunkDataList, metaDataList

    def _receiveFrame(self):
        chunkTypeList, chunkDataList, metaDataList = self._readChunks()
        if self._dataFormat in ["imeas"]:
            for idx, chunkType in enumerate(chunkTypeList):
                if chunkType == 900:
                    logger.debug("push channel data to algo debug")
                    self.pushChannelData(chunkDataList[idx])
                else:
                    logger.warning("Ignoring chunkType=%d", chunkType)
        else:
            full_data = bytearray()
            for id in self._chunkIDFilter:
                try:
                    index = chunkTypeList.index(id)
                    full_data.extend(chunkDataList[index])
                except ValueError:
                    logger.warning("Chunk ID %d not found", id)
                    full_data = bytearray()

            if len(full_data):
                self.put((self._dataFormat, full_data))

    def _receive(self):
        try:
            while True:
                self._receiveFrame()
        except Exception:
            if not self._finished:
                self._finished = True
                raise

    def _readAnswer(self, expReqTicket = None):
        if self._useCDLL:
            while True:
                buf, reqTicket = self._socket.readAnswer(timebarrier_ns=self._timebarrier)
                if len(buf) == 0:
                    raise socket.timeout()
                #logger.info("received data: %d bytes ticket=%s start=%s", bufLen.value, reqTicket.value, buf[:16])
                if reqTicket == expReqTicket or expReqTicket is None:
                    return buf, reqTicket
                else:
                    logger.warning("unexpected ticket")
        else:
            while True:
                answer = self._recvall(16)
                ticket = answer[0:4]
                ansLen = int(answer.split(b"L")[1])
                res = self._recvall(ansLen)
                assert res[:4] == ticket and len(res) == ansLen
                if expReqTicket is None or ticket == expReqTicket:
                    break
            # skip the repeated ticket number and the "\r\n" end
            return res[4:-2], ticket

    def _sendCommand(self, cmd):
        if self._useCDLL:
            assert False
        else:
            cmdLen = len(cmd) + 6
            self._socket.sendall(b"1000L%09d\r\n1000%s\r\n" % (cmdLen, cmd))
            answer, _ = self._readAnswer(b"1000")
            return answer

    def _xmlrpcServerProxy(self):
        host = self._ip if self._xmlrpcPort is None else ("%s:%d" % (self._ip, self._xmlrpcPort))
        prx = ServerProxy(uri="http://%s/api/rpc/v1/com.ifm.efector/" % host, transport=TimeoutTransport(self._xmlrpcTimeout))
        return prx

    def _enableAlgoDebug(self, enabled):
        self._pcicPort = self._pcicPortConfigured
        if self._source is not None:
            prx = self._xmlrpcServerProxy()
            prefix = ("ports", self._source) if self._source.startswith("port") else ("applications", "instances", self._source)
            logger.debug("AD prefix: %s", "/".join(prefix))
            if self._pcicPortConfigured is None:
                pcicPort = json.loads(prx.get(["/%s/data/pcicTCPPort" % ("/".join(prefix))]))
                logger.debug("pcicPort: %s", json.dumps(pcicPort))
                while isinstance(pcicPort, dict):
                    pcicPort = pcicPort[list(pcicPort.keys())[0]]
                self._pcicPort = pcicPort
            logger.debug("Using pcic port %d", self._pcicPort)
            logger.debug("set algo debug enabled=%s", enabled)
            # set the imager into run state, such that it starts to acquire data
            request = {"data" : {"algoDebugFlag": enabled}}
            if self._autostart:
                request["state"] = "RUN" if enabled else "CONF"
            for p in prefix[::-1]:
                request = {p: request}
            logger.debug("set(%s)", str(request))
            prx.set(json.dumps(request))

    def isLegacyVersion(self):
        if self._source is None:
            return False
        host = self._ip if self._xmlrpcPort is None else ("%s:%d" % (self._ip, self._xmlrpcPort))
        prx = ServerProxy(uri="http://%s/api/rpc/v1/com.ifm.efector/" % host, transport=TimeoutTransport(self._xmlrpcTimeout))
        euphratesVersion = prx.getSWVersion()["Main_Application"].split(".")
        try:
            if int(euphratesVersion[0]) == 0 and int(euphratesVersion[1]) < 16:
                return True
        except:
            pass
        return False

    def _on_new_ifm3dpy_frame(self, frame):
        if self._finished:
            # ignore frames after stopped.
            return
        try:
            if self._dataFormat == "imeas":
                if frame.has_buffer(ifm3dpy.buffer_id.ALGO_DEBUG):
                    # note that this function is called from another thread.
                    adbuf = frame.get_buffer(ifm3dpy.buffer_id.ALGO_DEBUG)
                    b = adbuf.tobytes()
                    if self.full():
                        logger.warning("queue seems to be full!")
                    self.pushChannelData(b)
            
            
            elif self._dataFormat == "O3Rjpeg":
                if (frame.has_buffer(ifm3dpy.buffer_id.JPEG_IMAGE) or
                        frame.has_buffer(ifm3dpy.buffer_id.O3R_RGB_IMAGE_INFO)):
                    jpeg = frame.get_buffer(ifm3dpy.buffer_id.JPEG_IMAGE)
                    info = frame.get_buffer(ifm3dpy.buffer_id.O3R_RGB_IMAGE_INFO)
                    full_data = bytearray()
                    full_data.extend(info)
                    full_data.extend(jpeg)
                    self.put((self._dataFormat, full_data))
            
            ## To handle 2D/3D/app streams for iVA
            elif self._dataFormat in self._ivaDataFormats:
                if any([
                        frame.has_buffer(default_values.DEFAULT_ODS_APP_BUFFER_CHECK),
                        frame.has_buffer(default_values.DEFAULT_2D_BUFFER_CHECK),
                        frame.has_buffer(default_values.DEFAULT_3D_BUFFER_CHECK),
                        ]):
                    
                    full_data = {
                                "frame":frame,
                                "stream_id": self._streamId,
                                "stream_idx":self._streamIdx
                                }
                    self._streamIdx += 1
                    self.put((self._dataFormat, full_data))

            else:
                raise RuntimeError("Unknown data format %s" % self._dataFormat)
        except:
            logger.exception("Error during on_new_ifm3dpy_frame callback!")

    def connect(self):
        """
        Connects to the sensor, enables algo debug on the specified stream and starts the working thread.
        """
        self._finished = False
        if self._useIfm3d:
            self._enableAlgoDebug(False)
            time.sleep(0.1)
            self._o3r = ifm3dpy.O3R(ip=self._ip, xmlrpc_port=self._xmlrpcPort if self._xmlrpcPort is not None else 80)
            self._fg = ifm3dpy.FrameGrabber(self._o3r, self._pcicPort)
            if self._threading:
                self._fg.on_new_frame(self._on_new_ifm3dpy_frame)
                self._fg.on_async_notification(
                    lambda msgid, msg, self=self: logger.warning("[ifm3d %s] %s: %s", self._source, msgid, msg))
                self._fg.on_async_error(
                    lambda ecode, emsg, self=self: logger.error("[ifm3d %s] %d: %s", self._source, ecode, emsg))
                self._fg.on_error(
                    lambda errmsg: logger.error("[ifm3d %s]: network error %s", self._source, errmsg))
            
            ## To handle app/3D AD stream
            if self._dataFormat == "imeas":
                self._fg.start([ifm3dpy.buffer_id.ALGO_DEBUG]).wait()
            ## To handle AD-2D stream
            elif self._dataFormat == "O3Rjpeg":
                self._fg.start([ifm3dpy.buffer_id.JPEG_IMAGE, ifm3dpy.buffer_id.O3R_RGB_IMAGE_INFO]).wait()
            ## To handle 2D stream for iVA
            elif self._dataFormat == "hdf5-compound-vlen":
                self._fg.start(default_values.DEFAULT_2D_BUFFER_ID_LIST).wait()
            ## To handle 3D stream for iVA
            elif self._dataFormat == "hdf5-compound" and self._streamName.startswith("o3r_tof"):
                self._fg.start(default_values.DEFAULT_3D_BUFFER_ID_LIST).wait()
            ## To handle app stream for iVA
            elif self._dataFormat == "hdf5-compound" and self._streamName.startswith("o3r_app"):
                self._fg.start(default_values.DEFAULT_ODS_BUFFER_ID_LIST).wait()            
            else:
                raise RuntimeError("Unknown data format %s" % self._dataFormat)
            
            if not self._iVA_stream_request:
                self._enableAlgoDebug(True)

        elif self._useCDLL:

            self._enableAlgoDebug(False)
            self._socket = pcicCtypes.Socket(self._ip, self._pcicPort)

            ans = self._socket.sendCommand(b"p0")
            if ans[-1] != b"*":
                raise RuntimeError("error sending p0: %s" % ans)

            # enable algo debug output
            logger.debug("PCIC:p%x" % self._pcicOutputConf)
            ans = self._socket.sendCommand(b"p%x" % self._pcicOutputConf)
            if ans[-1] != b"*":
                raise RuntimeError("error sending p%d: %s" % (self._pcicOutputConf, ans))

            self._enableAlgoDebug(True)

        else:

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logger.debug("disable algo debug")
            # before connection, turn off algo debug
            self._enableAlgoDebug(False)
            time.sleep(0.1)
            logger.debug("connect PCIC")
            self._socket.connect((self._ip, self._pcicPort))
            # self._socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            if not self.isLegacyVersion():
                # disable all result output
                logger.debug("PCIC:p0")
                ans = self._sendCommand(b"p0")
                if chr(ans[-1]) != "*":
                    raise RuntimeError("error sending p0: %s" % ans)
                # enable algo debug output
                logger.debug("PCIC:p%x" % self._pcicOutputConf)
                ans = self._sendCommand(b"p%x" % self._pcicOutputConf)
                if chr(ans[-1]) != "*":
                    raise RuntimeError("error sending p%d: %s" % (self._pcicOutputConf, ans))

            logger.debug("enable algo debug")
            self._enableAlgoDebug(True)
            if self._threading:
                self._thread = Thread(target=self._receive)
                self._thread.start()

    def disconnect(self):
        """
        Disconnects from the sensor and finishes the working thread.
        :return:
        """
        self._finished = True
        if self._useIfm3d:
            self._fg.stop().wait()
            del self._fg
            del self._o3r
            if not self._iVA_stream_request:
                self._enableAlgoDebug(False)
        elif self._useCDLL:
            self._socket.close()
            self._socket = None
        else:
            self._socket.close() # this is kind of a forced exit, read() functions will fail after the socket is closed
            self._enableAlgoDebug(False)
            if self._threading:
                self._thread.join()
                self._thread = None
            self._socket = None

    def isalive(self):
        """
        Returns whether the AD instance is connected or not
        :return:
        """
        return not self._finished

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", help="ip address of VPU", default="192.168.0.69")
    parser.add_argument("--source", help="algo debug source", default=None,
                        choices=[("port%d" % v) for v in range(7)] + [("app%d" % v) for v in range(10)])
    parser.add_argument("--pcicPort", help="pcic port, if set, the --port setting is ignored.", default=None, type=int)
    parser.add_argument("--threading", help="use threaded mode of ADReceiver", default=False, action="store_true")
    parser.add_argument("--timeout", help="timeout to be used in the get function", default=3.0, type=float)
    parser.add_argument("--frames", help="number of frames to be grabbed (-1 to grab forever)", default=-1, type=int)
    parser.add_argument("--interpret", help="interpret data (needs ifm_imeas package).", action="store_true")
    parser.add_argument("--loglevel", default="INFO")
    parser.add_argument("--autostart", default=False, action="store_true",
                        help="automatically put the source into RUN state.")

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    with ADReceiver(args.ip, args.source if args.pcicPort is None else None, args.pcicPort,
                    autoInterpret=args.interpret, threading=args.threading, xmlrpcTimeout=args.timeout,
                    autostart=args.autostart) as rcv:
        cnt = 0
        t0 = time.time()
        while True:
            try:
                logger.debug("receiving frame ...")
                data = rcv.get(timeout=args.timeout)
            except socket.timeout:
                logger.debug("timeout")
                continue
            if args.interpret:
                logger.info("received imeas channels: %s", data.keys())
            else:
                logger.info("received %d bytes", len(data))
            cnt += 1
            if cnt > args.frames and args.frames >= 0:
                logger.info("Received %d frames in %.3f seconds.", cnt, time.time() - t0)
                break
