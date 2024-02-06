#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import numpy as np
from scipy import ndimage

def rectify(invIntrinsic, modelID, image):
    fx, fy, mx, my, alpha, k1, k2, k3, k4, k5 = invIntrinsic[:10]

    x, y = np.meshgrid(np.arange(image.shape[1]), np.arange(image.shape[0]))

    # transformation of pixel coordinates to normalized camera coordinate system
    ud = ((x + 0.5) - mx) / fx
    vd = ((y + 0.5) - my) / fy

    if modelID in [0, 1]:  # Bouguet model
        # apply distortions
        rd2 = (ud * ud) + (vd * vd)
        radial = 1.0 + (rd2 * (k1 + (rd2 * (k2 + (rd2 * k5)))))
        h = 2 * ud * vd
        tangx = (k3 * h) + (k4 * (rd2 + (2 * ud * ud)))
        tangy = (k3 * (rd2 + (2 * vd * vd))) + (k4 * h)
        distorted_x = (ud * radial) + tangx
        distorted_y = (vd * radial) + tangy

    elif modelID in [2, 3]:  # fish eye model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, theta_max = invIntrinsic[:10]

        lxy = np.sqrt(ud**2 + vd**2)
        theta = np.arctan2(lxy, 0.5)
        phi = np.minimum(theta, theta_max) ** 2
        p_radial = 1 + phi * (k1 + phi * (k2 + phi * (k3 + phi * k4)))
        theta_s = p_radial * theta
        f_radial = np.choose(lxy > 0, (0, theta_s / lxy))
        distorted_x = f_radial * ud
        distorted_y = f_radial * vd

    else:
        raise RuntimeError("wrong modelID2D")

    # convert back to pixel coordinates for rectification
    ix = ((fx * (distorted_x + (alpha * distorted_y))) + mx) - 0.5
    iy = ((fy * distorted_y) + my) - 0.5

    im_rect = np.empty_like(image)
    if len(image.shape) == 2:
        im_rect = ndimage.map_coordinates(
            image, [iy.ravel(), ix.ravel()], order=3, mode="constant", cval=0
        ).reshape(image.shape[:2])
    else:
        for i in range(image.shape[2]):
            im_rect[:, :, i] = ndimage.map_coordinates(
                image[:, :, i],
                [iy.ravel(), ix.ravel()],
                order=3,
                mode="constant",
                cval=0,
            ).reshape(image.shape[:2])

    return im_rect
