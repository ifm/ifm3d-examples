# -*- coding: utf-8 -*-
import socket
import struct
from pprint import pprint

# Assuming these apps have already been set up:
PLC_app = "app1"
ODS_app = "app0"

# Set up the server
VPU_IP = "192.168.0.69"  # Bind to the embedded device IP
TCPPCIC_PORT = 51011  # The port to listen to

# Connect and recieve data
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.connect((VPU_IP, TCPPCIC_PORT))
max_buffer_size = 2048
received_data = server_socket.recv(max_buffer_size)
print(f"Received {len(received_data)} bytes")
server_socket.close()
print("Connection closed")

print()
print("====================================================")

print("PCIC packet header:")
# Output data format (as per the specification): ticket + Length + CR + LF + ticket + CONTENT + CR + LF`**
# Extract the ticket (first 4 bytes)
ticket = received_data[:4].decode("ascii")
# Print the ticket
print("Ticket:", ticket)
# Extract the Length (the part starting with 'L' and followed by 9 digits
length_str = received_data[4:14].decode("ascii")
# Print the length
print("Length:", length_str)
# Extract the CR and LF
cr = received_data[14:15]  # Carriage Return (ASCII 13)
lf = received_data[15:16]  # Line Feed (ASCII 10)
# Print the CR and LF bytes as raw byte values
print("Carriage Return (CR):", cr)
print("Line Feed (LF):", lf)
# Extract the Ticket again (should be the same as the first 4 bytes)
ticket_after_cr_lf = received_data[16:20].decode("ascii")
print("Ticket after CR and LF:", ticket_after_cr_lf)
# Extract the content
content = received_data[20:-2]  # Skip CR, LF
print("Content Length:", len(content))
# Content = star + data + stop
# Extract the star and stop bytes
star = content[:4].decode("ascii")
stop = content[-4:].decode("ascii")
# Print the star and stop bytes
print("Star:", star)
print("Stop:", stop)

print()
print("====================================================")


def pretty_byte_string(byte_data, wrap=True):
    row_width = 16
    formatted_lines = []
    for i in range(0, len(byte_data), row_width):
        chunk = byte_data[i : i + row_width]
        # Convert each byte to hex and join with spaces
        hex_line = " ".join(f"{b:02x}" for b in chunk)
        formatted_lines.append(hex_line)
    if wrap:
        return "\n".join(formatted_lines)
    else:
        return " ".join(formatted_lines)


plc_data = content[4:-4]
print("PLC data formatted as is done in ifmVisionAssistant>2.10.4.0:")
print(pretty_byte_string(plc_data[:64]) + "...")


def unpack_spec(spec, data, truncate=32):
    unpacked_data = {}
    for field, subspec in spec.items():
        if isinstance(subspec, tuple):
            start, size, fmt, units = subspec
            if fmt:
                unpacked_data[field] = struct.unpack(fmt, data[start : start + size])[0]
            else:
                # print( start, size, fmt, units)
                byte_string = data[start : start + size]
                if truncate and len(byte_string) > truncate:
                    unpacked_data[field] = (
                        pretty_byte_string(byte_string[:truncate], wrap=False) + "..."
                        f" omitting {len(byte_string)-truncate}"
                    )
                else:
                    unpacked_data[field] = pretty_byte_string(byte_string, wrap=False)
        elif isinstance(subspec, dict):
            unpacked_data[field] = unpack_spec(subspec, data)
        else:
            raise ValueError(f"Invalid spec format for field '{field}': {subspec}")
    return unpacked_data


# %%

plc_data_spec = {  # "Parameter": (start, size, format, units)
    "Chunk Header": {
        "Chunk Type": (0x0000, 4, "I", ""),
        "Chunk Size": (0x0004, 4, "I", "bytes"),
        "Header Size": (0x0008, 4, "I", "bytes"),
        "Header Version": (0x000C, 4, "I", ""),
        "Image Width": (0x0010, 4, "I", "px"),
        "Image Height": (0x0014, 4, "I", "px"),
        "Pixel Format": (0x0018, 4, "I", ""),
        "Time Stamp (Deprecated)": (0x001C, 4, "I", "µs"),
        "Frame Count": (0x0020, 4, "I", ""),
        "Status Code": (0x0024, 4, "I", ""),
        "Time Stamp Sec": (0x0028, 4, "I", "s"),
        "Time Stamp NSec": (0x002C, 4, "I", "ns"),
    },
    "PLC ethernet results v3.1": {
        "Protocol Version Major": (48, 1, "B", ""),
        "Protocol Version Minor": (49, 1, "B", ""),
        "frame size": (50, 2, "H", ""),
    },
    "ODS_result_data": {
        "Result Age Indicator": (52, 2, "H", ""),
        "ODS Severity": (54, 2, "H", ""),
        "Zone0": (56, 2, "H", ""),
        "Zone1": (58, 2, "H", ""),
        "Zone2": (60, 2, "H", ""),
        "Zone Config ID": (62, 4, "I", ""),
        "Time Stamp": (66, 8, "Q", ""),
        "Polar Grid": (74, 674, "", ""),  # raw bytes
    },
    "PDS_result_data": {
        "PDS0": {
            "PDS0_result_age_indicator": (1424, 2, "H", ""),
            "PDS0_severity": (1426, 2, "H", ""),
            "PDS0_command_id": (
                1428,
                2,
                "H",
                "",
            ),  # 1-getRack 2-getPallet 3-getItem 4-volCheck
            "PDS0_ticket": (1430, 2, "H", ""),
            "PDS0_timestamp": (1432, 8, "Q", ""),
            "PDS0_last_result": (1440, 32, "", ""),  # raw bytes
        },
        "PDS1": {
            "PDS1_result_age_indicator": (1472, 2, "H", ""),
            "PDS1_severity": (1474, 2, "H", ""),
            "PDS1_command_id": (
                1476,
                2,
                "H",
                "",
            ),  # 1-getRack 2-getPallet 3-getItem 4-volCheck
            "PDS1_ticket": (1478, 2, "H", ""),
            "PDS1_timestamp": (1480, 8, "Q", ""),
            "PDS1_last_result": (1488, 32, "", ""),  # raw bytes
        },
    },
    "Diagnostic data": {
        "diagnostic_counter": {
            "diag_slice_index": (1520, 2, "H", ""),
            "diag_slice_count": (1522, 2, "H", ""),
        },
        "diag0": {
            "source": (1524, 2, "H", ""),
            "severity": (1526, 2, "H", ""),
            "id": (1528, 4, "I", ""),
        },
        "diag1": {
            "source": (1532, 2, "H", ""),
            "severity": (1534, 2, "H", ""),
            "id": (1536, 4, "I", ""),
        },
        "diag2": {
            "source": (1540, 2, "H", ""),
            "severity": (1542, 2, "H", ""),
            "id": (1544, 4, "I", ""),
        },
        "diag3": {
            "source": (1548, 2, "H", ""),
            "severity": (1550, 2, "H", ""),
            "id": (1552, 4, "I", ""),
        },
        "diag4": {
            "source": (1556, 2, "H", ""),
            "severity": (1558, 2, "H", ""),
            "id": (1560, 4, "I", ""),
        },
        "diag5": {
            "source": (1564, 2, "H", ""),
            "severity": (1566, 2, "H", ""),
            "id": (1568, 4, "I", ""),
        },
        "diag6": {
            "source": (1572, 2, "H", ""),
            "severity": (1574, 2, "H", ""),
            "id": (1576, 4, "I", ""),
        },
        "diag7": {
            "source": (1580, 2, "H", ""),
            "severity": (1582, 2, "H", ""),
            "id": (1584, 4, "I", ""),
        },
        "diag8": {
            "source": (1596, 2, "H", ""),
            "severity": (1598, 2, "H", ""),
            "id": (1600, 4, "I", ""),
        },
        "diag9": {
            "source": (1604, 2, "H", ""),
            "severity": (1606, 2, "H", ""),
            "id": (1608, 4, "I", ""),
        },
        "diag10": {
            "source": (1612, 2, "H", ""),
            "severity": (1614, 2, "H", ""),
            "id": (1616, 4, "I", ""),
        },
        # "diag11": {
        #    "source": (1620, 2, "H", ""),
        #    "severity": (1622, 2, "H", ""),
        #    "id": (1624, 4, "I", ""),
        # },
        # "diag12": {
        #    "source": (1632, 2, "H", ""),
        #    "severity": (1634, 2, "H", ""),
        #    "id": (1636, 4, "I", ""),
        # },
        # "diag13": {
        #    "source": (1640, 2, "H", ""),
        #    "severity": (1642, 2, "H", ""),
        #    "id": (1644, 4, "I", ""),
        # },
        # "diag14": {
        #    "source": (1652, 2, "H", ""),
        #    "severity": (1654, 2, "H", ""),
        #    "id": (1656, 4, "I", ""),
        # },
        # "diag15": {
        #    "source": (1660, 2, "H", ""),
        #    "severity": (1662, 2, "H", ""),
        #    "id": (1664, 4, "I", ""),
        # },
        # "diag16": {
        #    "source": (1672, 2, "H", ""),
        #    "severity": (1674, 2, "H", ""),
        #    "id": (1676, 4, "I", ""),
        # },
        "plc_app": {
            "group_severity": (1684, 2, "H", ""),
        },
    },
}

pprint(unpack_spec(plc_data_spec, plc_data), sort_dicts=False)
