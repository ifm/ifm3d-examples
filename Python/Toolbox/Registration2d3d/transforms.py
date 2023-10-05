#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import numpy as np
from scipy import ndimage


def intrinsic_projection(intrinsicModelID, intrinsicModelParameters, width, height):
    """Evaluate intrinsic calibration model parameter and return unit vectors in the optical reference system

    Args:
        intrinsicModelID (int): intrinsic model id
        intrinsicModelParameters (numpy array): intrinsics model parameter as returned from the camera (as part of the image chunk)
        width (int): image width
        height (int): image height

    Raises:
        RuntimeError: raises Runtime error if modelID doesn't exist

    Returns:
        tuple: direction vector in the optical reference system
    """

    if intrinsicModelID == 0:  # Bouguet model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, k5 = intrinsicModelParameters[:10]
        iy, ix = np.indices((height, width))
        cx = (ix + 0.5 - mx) / fx
        cy = (iy + 0.5 - my) / fy
        cx -= alpha * cy
        r2 = cx ** 2 + cy ** 2
        fradial = 1 + r2 * (k1 + r2 * (k2 + r2 * k5))
        h = 2 * cx * cy
        tx = k3 * h + k4 * (r2 + 2 * cx ** 2)
        ty = k3 * (r2 + 2 * cy ** 2) + k4 * h
        dx = fradial * cx + tx
        dy = fradial * cy + ty
        fnorm = 1 / np.sqrt(dx ** 2 + dy ** 2 + 1)
        vx = fnorm * dx
        vy = fnorm * dy
        vz = fnorm
        return vx, vy, vz
    elif intrinsicModelID == 2:  # fish eye model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, theta_max = intrinsicModelParameters[:10]
        iy, ix = np.indices((height, width))
        cx = (ix + 0.5 - mx) / fx
        cy = (iy + 0.5 - my) / fy
        cx -= alpha * cy
        theta_s = np.sqrt(cx ** 2 + cy ** 2)
        phi_s = np.minimum(theta_s, theta_max)
        p_radial = 1 + phi_s ** 2 * (
            k1 + phi_s ** 2 * (k2 + phi_s ** 2 * (k3 + phi_s ** 2 * k4))
        )
        theta = theta_s * p_radial
        theta = np.clip(
            theta, 0, np.pi
        )  # -> avoid surprises at image corners of extreme fisheyes
        vx = np.choose((theta_s > 0), (0, (cx / theta_s) * np.sin(theta)))
        vy = np.choose((theta_s > 0), (0, (cy / theta_s) * np.sin(theta)))
        vz = np.cos(theta)
        return vx, vy, vz
    else:
        raise RuntimeError("Unknown model %d" % intrinsicModelID)


def rotMat(r, order=(0, 1, 2)):
    R = np.eye(3)
    for i in order:
        lr = np.eye(3)
        lr[(i + 1) % 3, (i + 1) % 3] = np.cos(r[i])
        lr[(i + 2) % 3, (i + 2) % 3] = np.cos(r[i])
        lr[(i + 1) % 3, (i + 2) % 3] = -np.sin(r[i])
        lr[(i + 2) % 3, (i + 1) % 3] = np.sin(r[i])
        R = R.dot(lr)
    return R


def translate(pcd, X, Y, Z) -> np.ndarray:
    return np.array(pcd) + np.array((X, Y, Z))[..., np.newaxis]


def rotate_xyz(pcd, rotX, rotY, rotZ) -> np.ndarray:
    return rotMat(np.array((rotX, rotY, rotZ))).dot(pcd)


def rotate_zyx(pcd, rotX, rotY, rotZ) -> np.ndarray:
    return rotMat(np.array((rotX, rotY, rotZ)), order=(2, 1, 0)).dot(pcd)


def inverse_intrinsic_projection(pcd, invIntrinsic2D, modelID2D):
    """inverse intrinsic projection model evaluation

    Args:
        pcd (numpy array): point cloud data
        invIntrinsic2D (numpy array): inverse intrinsics model parameters
        modelID2D (int): model ID
        extrinsic2D (numpy array): extrinsic model parameters: [translation, rotation]

    Raises:
        RuntimeError: raised if model ID is not valid

    Returns:
        tuple: image coordinates in pixel coordinate system: upper left corner is (0,0)
    """

    tz = np.maximum(0.001, pcd[2, :])
    ixn = pcd[0, :] / tz
    iyn = pcd[1, :] / tz

    # apply distortion
    if modelID2D in [0, 1]:  # Bouguet model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, k5 = invIntrinsic2D[:10]

        rd2 = ixn ** 2 + iyn ** 2
        radial = rd2 * (k1 + rd2 * (k2 + rd2 * k5)) + 1
        ixd = ixn * radial
        iyd = iyn * radial
        if k3 != 0 or k4 != 0:
            h = 2 * ixn * iyn
            tangx = k3 * h + k4 * (rd2 + 2 * ixn ** 2)
            tangy = k3 * (rd2 + 2 * iyn ** 2) + k4 * h
            ixd += tangx
            iyd += tangy
        # transform to imager
        ix = ((fx * (ixd + alpha * iyd)) + mx) - 0.5
        iy = ((fy * (iyd)) + my) - 0.5

    elif modelID2D in [2, 3]:  # fish eye model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, theta_max = invIntrinsic2D[:10]

        lxy = np.sqrt(pcd[0, :] ** 2 + pcd[1, :] ** 2)
        theta = np.arctan2(lxy, pcd[2, :])
        phi = np.minimum(theta, theta_max) ** 2
        p_radial = 1 + phi * (k1 + phi * (k2 + phi * (k3 + phi * k4)))
        theta_s = p_radial * theta
        f_radial = np.choose(lxy > 0, (0, theta_s / lxy))
        ixd = f_radial * pcd[0, :]
        iyd = f_radial * pcd[1, :]

        ix = ixd * fx - 0.5 + mx - alpha * iyd * fx
        iy = iyd * fy - 0.5 + my

    else:
        raise RuntimeError("Unknown intrinsic model ID %d" % invIntrinsic2D["modelID"])

    return np.vstack([ix, iy])


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

        lxy = np.sqrt(ud ** 2 + vd ** 2)
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
