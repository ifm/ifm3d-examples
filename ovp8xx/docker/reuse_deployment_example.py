# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from deployment_examples import demo_deployment_components, deploy
from attach_to_container import attach

import os

IP = os.environ.get("IFM3D_IP", "192.168.0.69")

# %%
output_from_container = deploy(
    ip=IP,
    service_name = "python",
    additional_deployment_components=demo_deployment_components,
    seconds_of_output=10
)
# %%
output_from_container = deploy(
    ip=IP,
    service_name = "python",
    additional_deployment_components=demo_deployment_components,
    tar_file_image_transfer=False,
    seconds_of_output=10
)
# %%
output_from_container = attach(
    IP = IP,
    seconds_of_output=20
)
# %%
