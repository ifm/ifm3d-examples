# Control-logix

This adapter provides communications between the O3R system control-logix PLCs using the pycomm3 library. No guarantees are provided as the the performance of this library. The authors of this repository have no affiliation with Allen-Bradley.

Using this adapter, the PLC can tell the VPU which set of zones to deliver occupancy data for, and the VPU will return a signal including it's status, and whether or not the given zones are occupied.

## 0. Setup of Logix Controller

### 0.1 Required Tags:

The O3R utilizes CIP messages to write to 2 tags on the controller. These must match the following spelling and data-types exactly for the application to run as expected:

"ifm_o3r_vpu_signal" -> ULINT
"ifm_o3r_zone_idx"  -> UDINT 

#### "ifm_o3r_vpu_signal" -> ULINT

This tag contains all data that the VPU will send to the controller. The following are the basic components of the current spec:

##### "heartbeat":

    "offset": 0,
    "width" : 1,
    "type": "BOOL",
    "desc": "Switches from 0 to 1 to indicate active connection from VPU",
    "default_value": 1

##### "status":

    "offset":1,
    "width": 8,
    "type": "USINT",
    "desc": "status code",
    "default_value": 01111110,

##### "zone_1_occupancy":

    "offset": 9,
    "width" : 1,
    "type": "BOOL",
    "desc": "Whether or not zone is occupied",
    "default_value": 1,

##### "zone_2_occupancy":

    "offset": 10,
    "width" : 1,
    "type": "BOOL",
    "desc": "Whether or not zone is occupied",
    "default_value": 1,

##### "zone_3_occupancy":
    
    "offset": 11,
    "width" : 1,
    "type": "BOOL",
    "desc": "Whether or not zone is occupied",
    "default_value": 1

#### "ifm_o3r_zone_idx"  -> UDINT 

This tag indicates which zone-set the VPU should load up

0 means that the vpu will idle. Setting the VPU to Idle will save power. The vpu will NOTE: It will take up to 2 seconds for the vpu heartbeat to return
