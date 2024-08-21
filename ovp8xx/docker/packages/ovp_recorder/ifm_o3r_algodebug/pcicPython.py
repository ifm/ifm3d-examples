import ctypes as ct
import logging
import select
import socket
import time

adrcv = "simulated"

logger = logging.getLogger(__name__)

class PcicException(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)

class FatalPcicException(PcicException):
    pass

class Socket:
    def __init__(self, ip, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._recvBuffer = bytearray(b"\0"*(10*1024*1024)) # 10 MB receive buffer, maximum size of a single AD channel
        self._socket.connect((ip, port))

    def __del__(self):
        if self._socket is not None:
            self.close()

    def close(self):
        e = None
        try:
            self._socket.shutdown(socket.SHUT_WR)
        except Exception as e:
            pass
        self._socket.close()
        self._socket = None
        if e is not None:
            raise e

    def sendall(self, buffer):
        self._socket.sendall(buffer)

    def sendCommand(self, cmd, timebarrier_ns=0):
        buf = b"1000L%09d\r\n1000%s\r\n" % (len(cmd) + 6, cmd)
        self.sendall(buf)
        while True:
            ans, ticket = self.readAnswer(timebarrier_ns=timebarrier_ns)
            if ticket == b"1000":
                return ans

    def _waitForReadyRead(self, timebarrier_ns):
        tnow = self.gettime()
        timeout_ns = timebarrier_ns - tnow if timebarrier_ns > tnow else 0
        cnt = 0
        while timeout_ns >= 0:
            try:
                rlist, _, _ = select.select([self._socket], [], [], timeout_ns*1e-9)
                if len(rlist) > 0:
                    return
                tnow = self.gettime()
                timeout_ns = timebarrier_ns - tnow if timebarrier_ns > tnow else 0
                if timeout_ns == 0:
                    raise BlockingIOError()
            except Exception as e:
                if isinstance(e, BlockingIOError):
                    raise socket.timeout()
                else:
                    raise FatalPcicException("connection lost")

    def _read(self, numBytes, timebarrier_ns, buf=None):
        bytesRead = 0
        if buf is None:
            buf = bytearray(b"\0"*numBytes)
        view = memoryview(buf)
        while bytesRead < numBytes:
            if timebarrier_ns > 0:
                self._waitForReadyRead(timebarrier_ns)
            ret = self._socket.recv_into(view, numBytes - bytesRead)
            view = view[ret:]
            if ret == 0:
                raise FatalPcicException("Protocol error: connection closed")
            bytesRead += ret
        return buf

    def readAnswer(self, timebarrier_ns=0):
        timebarrierRelaxed = timebarrier_ns + 500000000 if timebarrier_ns > 0 else 0
        if timebarrier_ns > 0:
            self._waitForReadyRead(timebarrier_ns)
        ansTicket = self._read(16, timebarrierRelaxed)
        if ansTicket[4:5] != b"L":
            logger.warning("received: %s", ansTicket)
            raise FatalPcicException("Protocol error: expected L on char no 5")
        tmpLen = int(ansTicket[5:])
        if tmpLen > len(self._recvBuffer):
            self._read(tmpLen, timebarrierRelaxed)
        self._read(4, timebarrierRelaxed)
        tmpLen -= 4
        self._read(tmpLen-2, timebarrierRelaxed, self._recvBuffer)
        self._read(2, timebarrierRelaxed)
        ansLen = tmpLen-2
        ticket = ansTicket[:4]
        return (ct.c_char*ansLen).from_buffer(self._recvBuffer), ticket

    def setblocking(self, blocking):
        self._socket.setblocking(blocking)

    def gettime(self):
        return time.monotonic_ns()
