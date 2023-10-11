# tinycan

##  specification:

Transmit
    TPDO1         - 0x180 + Node ID
        - byte1+2 - zone index 
        - byte3+4 - VPU status
        - byte5+6 - occupancy data
    Heartbeat - 0x700 + Node ID

Receive
    NMT state setting commands
    Sync - 0x80  (optional)
    RPDO1 - 0x200 + Node ID
        - byte1+2 - zone index 
 
## get started

Define config per system -> config.json
    modify defaults per the system requirements

"adapters":[
    {
        "type":"tinycan",
        "params":{
            "controller": 1,
            "reciever": 1,
            "log_level": "info",
            "managed_id": "0x64",
            "ods_framerate": 20,
            "bustype": "socketcan",
            "bitrate": 125000,
            "sync_offset_ms": -1,
            "heartbeat_time_ms": 1000
        }
    },
    {
        "type":"rest",
        "params":{
            "controller": 0,
            "reciever": 1,
            "port":8000
        }
    }
]

Deploy application to VPU via o3rdock -> see deploy/readme.md
Attempt connection via CANopen stack ...

Avoid checking:
- vendor ID
- product number
- revision number
... this behavior is not handled

