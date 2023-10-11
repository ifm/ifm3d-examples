#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
from typing import List
from pydantic import BaseModel
from pydantic import Field

ZONES_ID_WHEN_UNCONFIGURED = 65536


class AdHocZoneSetting(BaseModel):
    zone0: List = Field([[0, 1], [1, 1], [1, -1], [0, -1]], max_items=6, min_items=3)
    zone1: List = Field([[1, 1], [2, 1], [2, -1], [1, -1]], max_items=6, min_items=3)
    zone2: List = Field(
        [[2, 1], [3.5, 1], [3.5, -1], [2, -1]], max_items=6, min_items=3
    )
    index: int = ZONES_ID_WHEN_UNCONFIGURED
    maxHeight: float = 0.5  # m
    view: str = ""


class ZoneSet(BaseModel):
    index: int = 0
