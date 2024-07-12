# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from deployment_examples import demo_deployment_components, deploy

# %%
deploy(
    service_name = "python",
    additional_deployment_components=demo_deployment_components,
    seconds_of_output=10
)
# %%
deploy(
    service_name = "python",
    additional_deployment_components=demo_deployment_components,
    tar_file_image_transfer=False,
    seconds_of_output=10
)