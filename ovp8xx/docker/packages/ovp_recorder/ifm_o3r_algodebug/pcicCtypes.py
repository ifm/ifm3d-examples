import ctypes as ct
import logging

logger = logging.getLogger(__name__)

adrcv = None
def _load_adrcv():
    global adrcv
    adrcv = ct.CDLL(r"C:\Projects\iCV-Algo\O3R\delivery\msvc140_x86_64\release\lib\adrcv.dll")
    adrcv.ad_connect.restype = ct.c_int64
    adrcv.ad_connect.argtypes = [ct.c_char_p, ct.c_uint16, ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32)]
    adrcv.ad_disconnect.restype = ct.c_int32
    adrcv.ad_disconnect.argtypes = [ct.c_int64, ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32)]
    adrcv.ad_socket_send_all.restype = ct.c_int32
    adrcv.ad_socket_send_all.argtypes = [ct.c_int64, ct.c_char_p, ct.c_uint32, ct.POINTER(ct.c_int32),
                                         ct.POINTER(ct.c_int32)]
    adrcv.ad_sendCommand.restype = ct.c_int32
    adrcv.ad_sendCommand.argtypes = [ct.c_int64, ct.c_char_p, ct.c_uint32, ct.c_char_p, ct.POINTER(ct.c_uint32),
                                     ct.c_uint64, ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32)]
    adrcv.ad_readAnswer.restype = ct.c_int32
    adrcv.ad_readAnswer.argtypes = [ct.c_int64, ct.c_char_p, ct.c_char_p, ct.POINTER(ct.c_uint32), ct.c_uint64,
                                    ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32)]
    adrcv.ad_setBlocking.restype = ct.c_int32
    adrcv.ad_setBlocking.argtypes = [ct.c_int64, ct.c_int32, ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32)]
    adrcv.ad_strerror.argtypes = [ct.c_int32, ct.c_int32, ct.c_char_p, ct.c_uint32]
    adrcv.ad_gettime.restype = ct.c_uint64

_load_adrcv()

class PcicException(RuntimeError):
    def __init__(self, err, errdomain):
        msg = ct.create_string_buffer(b"", 1024)
        adrcv.ad_strerror(err, errdomain, msg, 1024)
        assert isinstance(msg.value, bytes)
        super().__init__(msg.value.decode(errors='ignore'))

class FatalPcicException(PcicException):
    pass

def raisePcicException(err, errdomain):
    if errdomain.value == 3:
        e = FatalPcicException
    else:
        e = PcicException
    raise e(err, errdomain)

class Socket:
    def __init__(self, ip, port):
        self._socket = None
        self._recvBuffer = ct.create_string_buffer(b"", 10*1024*1024) # 10 MB receive buffer, maximum size of a single AD channel
        if isinstance(ip, str):
            ip = ip.encode()
        err = ct.c_int32()
        errdomain = ct.c_int32()
        ret = adrcv.ad_connect(ip, port, ct.byref(err), ct.byref(errdomain))
        if ret < 0:
            raisePcicException(err, errdomain)
        self._socket = ret

    def __del__(self):
        if self._socket is not None:
            self.close()

    def close(self):
        err = ct.c_int32()
        errdomain = ct.c_int32()
        ret = adrcv.ad_disconnect(self._socket, ct.byref(err), ct.byref(errdomain))
        self._socket = None
        if ret != 0:
            raisePcicException(err, errdomain)

    def sendall(self, buffer):
        err = ct.c_int32()
        errdomain = ct.c_int32()
        ret = adrcv.ad_socket_send_all(self._socket, buffer, len(buffer), ct.byref(err), ct.byref(errdomain))
        if ret != 0:
            raisePcicException(err, errdomain)

    def sendCommand(self, cmd, timebarrier_ns=0):
        err = ct.c_int32()
        errdomain = ct.c_int32()
        buflen = ct.c_uint32(len(self._recvBuffer))
        ret = adrcv.ad_sendCommand(self._socket, cmd, len(cmd), self._recvBuffer, ct.byref(buflen), timebarrier_ns, ct.byref(err), ct.byref(errdomain))
        if ret:
            raisePcicException(err, errdomain)
        return ct.cast(ct.pointer(self._recvBuffer), ct.POINTER(ct.c_char*buflen.value)).contents

    def readAnswer(self, timebarrier_ns=0):
        err = ct.c_int32()
        errdomain = ct.c_int32()
        reqTicket = (ct.c_char * 5)()
        buflen = ct.c_uint32(len(self._recvBuffer))
        ret = adrcv.ad_readAnswer(self._socket, reqTicket, self._recvBuffer, ct.byref(buflen), timebarrier_ns, ct.byref(err), ct.byref(errdomain))
        if ret:
            raisePcicException(err, errdomain)
        return ct.cast(ct.pointer(self._recvBuffer), ct.POINTER(ct.c_char*buflen.value)).contents, reqTicket.value

    def setblocking(self, blocking):
        err = ct.c_int32()
        errdomain = ct.c_int32()
        ret = adrcv.ad_setBlocking(self._socket, 1 if blocking else 0, ct.byref(err), ct.byref(errdomain))
        if ret:
            raisePcicException(err, errdomain)

    def gettime(self):
        return adrcv.ad_gettime()
