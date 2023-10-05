#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# collect configuration + dormant/active ODS errors
# %%
from ifm3dpy import O3R

from get_diagnostic import O3RDiagnostic

from pathlib import Path
from datetime import datetime
import json
from time import sleep

addr = "192.168.10.69"
o3r = O3R(addr)

project_dir = Path(__file__).parent.parent

# %%
o3r_diagnostic = O3RDiagnostic()
vpu_name = "Malvern"
conf = o3r.get()
diags = o3r_diagnostic.get_filtered_diagnostic_msgs(addr, False)
print(diags)

# # VPU needs a reboot for ODS diagnostic messages to go dormant
# o3r.reboot()
# sleep(60)
# %%

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
curr_dump_dir = project_dir
for directory in ("dumps", vpu_name, timestamp):
    curr_dump_dir = curr_dump_dir / directory
    try:
        curr_dump_dir.mkdir()
    except FileExistsError:
        print(f"Directory {curr_dump_dir} already exists. Skipping creation.")

with open(curr_dump_dir / "conf.json", "w") as f:
    f.write(json.dumps(conf, indent=4))
with open(curr_dump_dir / "diags.json", "w") as f:
    f.write(json.dumps(diags, indent=4))

# %%
