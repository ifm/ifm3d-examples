# -*- coding: utf-8 -*-
import socket
import struct


def f_command(parameter_id, reserved, value):
    """
    For commands with a single 2-byte value (uint16).
    """
    ticket = "1234"
    command_suffix = "\r\n"
    value_bytes = value.to_bytes(2, byteorder="little")
    version_bytes = bytes.fromhex("0101")
    content = (
        ticket.encode("ascii")
        + b"f"
        + parameter_id.encode("ascii")
        + reserved.encode("ascii")
        + version_bytes
        + value_bytes
        + command_suffix.encode("ascii")
    )
    length_str = f"L{len(content):09d}"
    header = ticket + length_str + command_suffix
    full_message = header.encode("ascii") + content
    return full_message


def f_command_multi(
    parameter_id, reserved, app_id, depth_hint, pallet_index, pallet_order
):
    """
    For commands with multiple values (getPallet: 1x uint16, 3x int16).
    """
    ticket = "1234"
    command_suffix = "\r\n"
    # Pack values: uint16, int16, int16, int16 (all little endian)
    value_bytes = struct.pack("<Hhhh", app_id, depth_hint, pallet_index, pallet_order)
    version_bytes = bytes.fromhex("0101")
    content = (
        ticket.encode("ascii")
        + b"f"
        + parameter_id.encode("ascii")
        + reserved.encode("ascii")
        + version_bytes
        + value_bytes
        + command_suffix.encode("ascii")
    )
    length_str = f"L{len(content):09d}"
    header = ticket + length_str + command_suffix
    full_message = header.encode("ascii") + content
    return full_message


if __name__ == "__main__":
    ip = "192.168.0.69"
    app_port = 51011

    # Example for getPallet (multi-value)
    parameter_id = "02200"
    reserved = "#00000"
    app_id = 0  # uint16
    depth_hint = -1  # int16
    pallet_index = 0  # int16
    pallet_order = 0  # int16

    full_message = f_command_multi(
        parameter_id, reserved, app_id, depth_hint, pallet_index, pallet_order
    )
    print(repr(full_message.decode("latin1")))

    # Example for single-value command (uncomment to test)
    # parameter_id = "02101"
    # reserved = "#00000"
    # value = 2
    # full_message = f_command(parameter_id, reserved, value)
    # print(repr(full_message.decode("latin1")))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, app_port))
            s.sendall(full_message)
    except Exception as e:
        print(f"Error: {e}")
