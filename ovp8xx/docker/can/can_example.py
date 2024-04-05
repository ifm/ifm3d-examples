#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
#!/usr/bin/env python3
import time
import canopen


def connect():
    nw = canopen.Network()
    nw.connect(channel="can0", bustype="socketcan")
    nw.scanner.search()
    time.sleep(0.05)

    device = nw.add_node(nw.scanner.nodes[0], "/usr/local/share/DTM425.eds")
    device.nmt.state = "OPERATIONAL"
    time.sleep(0.05)

    return (nw, device)


def disconnect(nw, device):
    device.nmt.state = "PRE-OPERATIONAL"
    nw.disconnect()


def write_tag(device, data):
    memory_size = device.sdo[0x2182][0x4].raw

    if len(data) < memory_size:
        data = data + b'\x00' * (memory_size - len(data))

    for offset in range(0, memory_size, 8):
        length = (8 if offset + 8 <= memory_size else
                  memory_size - offset)
        device.sdo[0x2380].raw = offset
        device.sdo[0x2381].raw = length
        device.sdo[0x2382].raw = data[offset:offset + length]


def read_tag(device):
    memory_size = device.sdo[0x2182][0x4].raw
    data = b""

    for offset in range(0, memory_size, 8):
        length = 8 if offset + 8 <= memory_size else memory_size - offset
        device.sdo[0x2280].raw = offset
        device.sdo[0x2281].raw = length
        data = data + device.sdo[0x2282].raw

    return data


def main():
    nw, device = connect()
    data = b'\xDE\xAD\xBE\xEF'
    print("Writing tag:", data)
    write_tag(device, data)
    print("Reading tag:", read_tag(device))
    disconnect(nw, device)

if __name__ == "__main__":
    main()