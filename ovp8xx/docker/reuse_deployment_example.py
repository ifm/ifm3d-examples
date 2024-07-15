# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import os
from pprint import pprint

from deployment_examples import deploy
from deployment_components import demo_deployment_components
from attach_to_container import attach

IP = os.environ.get("IFM3D_IP", "192.168.0.69")

print(f"Using IP: {IP}")
print("Available demo services:")
pprint(list(demo_deployment_components.keys()))

# %%
output_from_container = deploy(
    ip=IP,
    service_name = "cpp_multi_head",
    additional_deployment_components=demo_deployment_components,
    seconds_of_output=30
)
# %%
output_from_container = deploy(
    ip=IP,
    service_name = "python",
    additional_deployment_components=demo_deployment_components,
    tar_image_transfer=False,
    seconds_of_output=10
)
# %%
output_from_container = attach(
    IP = IP,
    seconds_of_output=20
)
# %%
