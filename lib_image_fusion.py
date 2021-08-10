from numpy import zeros, flip, reshape, meshgrid, column_stack, linspace, full, sum, min, max, mean, isnan, nan_to_num
from numpy import sqrt, log, uint8, savetxt, loadtxt, uint16

from glob import glob
from datetime import datetime
from pickle import load, dump
from os import remove, makedirs, listdir
from os.path import exists, join

from cv2 import resize, cvtColor, COLOR_BGR2GRAY, GaussianBlur, imwrite, IMWRITE_PNG_COMPRESSION#, imread, IMREAD_UNCHANGED
from scipy.ndimage import median_filter

import png


# Function that controls the methods calling in the mearging image task.
def _merge_visible(F):
    F._crop_images()
    F._color_gray()
    F._merge_images()


class _fusion():
    """
    Object that contains the global variables and main methods
    on the image fusion algorithm.

    """
    def __init__(self, dir, s = 1, N = (480, 640)):
        self._dir_in  = dir
        self._dir_out = dir
        self._s       = s
        self._N       = N
        self._c       = (self._N[0] / 2, self._N[1] / 2)

        self._X, self._Y = meshgrid(linspace(0, self._N[1] - 1, self._N[1]), linspace(0, self._N[0] - 1, self._N[0]))
        self._mask       = self.__create_masks(r = [5, 6.25, 12.5, 25])
        self._idx        = sqrt((self._X - self._c[1])**2 + (self._Y - self._c[0])**2) <= 217.5


    def _get(self, data):
        self._images = []

        for i in range(data.shape[0]):
            self._images.append(data[i, ...].astype('float32'))
            #self._images.append(data[..., i*3:(i + 1)*3].astype('float32'))  # Load the images taken with 4 different exposition and append them together


    def _update(self, data):
        #self._unix = unix     # UNIX time of the current image.
        self._get(data)       # List of current image at different exposure times.


    def _return(self):
        return self._VI[15:465, 95:545].copy()


    def _save(self, unix):

        self._unix = int(unix)

        with open('{}{:010}VI.png'.format(self._dir_out, self._unix), 'wb') as f:
            writer = png.Writer(width = 450, height = 450, bitdepth = 16, compression = None, greyscale = True)
            writer.write(f, self._VI[15:465, 95:545].tolist())
        #print(name)

    # FUNCTION TO ADJUNST THE WHITE BALANCE AND TRANSFOR TO GRAY SCALE THE CORRECTED IMAGES
    def _white_balance(self, img):
        img = img.astype('uint16')

        # Separte RGB color components and calculate their average
        mRed   = mean(img[..., 0])
        mGreen = mean(img[..., 1])
        mBlue  = mean(img[..., 2])

        # Estimate a costant for white balance using gray image average as reference
        mGray = mean(cvtColor(img, COLOR_BGR2GRAY))

        # Adjust each element in the RGB components with respect to the white balance constant
        img[..., 0] = img[..., 0] * (mGray / mRed)
        img[..., 1] = img[..., 1] * (mGray / mGreen)
        img[..., 2] = img[..., 2] * (mGray / mBlue)
        img[(img >= 255.)] = 255.
        img[~self._idx, :] = 0.
        return img[15:465, 95:545, :].astype('uint8')

    ## In this part of code are implemented the funcitons for the Image Fusion.
    def __circumference_mask(self, r):
        M = (sqrt((self._X - self._c[1])**2 + (self._Y - self._c[0])**2) <= r) * 255.
        return M / max(M)

    # FUNCTION TO DEFINE THE CIRCULAR MASKS
    def __create_masks(self, r = [4, 16, 28, 44]):
        M = []; M_outter = []; M_inner  = []; C_outter = []; C_inner  = []; G = []

        for idx in range(len(r)):
            img_mask   = self.__circumference_mask(r[idx])
            img_outter = self.__circumference_mask(r[idx] + 2)
            img_inner  = self.__circumference_mask(r[idx] - 2)

            M.append(img_mask)
            M_outter.append(img_outter)
            M_inner.append(img_inner)
            C_outter.append(img_outter * img_mask)
            C_inner.append(img_inner * img_mask)
            G.append(GaussianBlur(img_mask, (15, 15), 7.5))
        return [M, M_outter, M_inner, C_outter, C_inner, G]

    # FUNCTION TO CROP THE IMAGES TO THE RIGHT SIZE
    def _crop_images(self):
        images_crop = []

        for img in self._images:

            if isnan(img).any():
                img = nan_to_num(img) + .001

            images_crop.append(img)
        self._images = images_crop


    def _color_gray(self):
        images_gray = []
        for img, i in zip(self._images, range(len(self._images))):
            images_gray.append(cvtColor(img, COLOR_BGR2GRAY))

        self._images = images_gray


    # FUNCTION TO APPLY THE MASK AND MERGE TOGETHER THE DIFFERENT EXPOSURES TIMES IMAGES
    def _merge_images(self):

        # Defining variable weights for the model
        A_1 = 1.
        A_2 = A_1 * mean(self._images[0] * self._mask[4][0]) / mean(self._images[1] * self._mask[3][0])
        A_3 = A_2 * mean(self._images[1] * self._mask[4][1]) / mean(self._images[2] * self._mask[3][1])
        A_4 = A_3 * mean(self._images[2] * self._mask[4][2]) / mean(self._images[3] * self._mask[3][2])
        A   = [A_1, A_2, A_3, A_4]

        # Definining equation and computing merged image
        X_4 = (1 - self._mask[5][3]) * (self._images[0] * A[0] + self._images[1] * A[1] + self._images[2] * A[2] + self._images[3] * A[3]) / 4.
        X_3 = self._mask[5][3] * (1 - self._mask[5][2]) * (self._images[0] * A[0] + self._images[1] * A[1] + self._images[2] * A[2]) / 3.
        X_2 = self._mask[5][2] * (1 - self._mask[5][1]) * (self._images[0] * A[0] + self._images[1] * A[1]) / 2.
        X_1 = self._mask[5][1] * self._images[0] * A[0]
        X   = X_1 + X_2 + X_3 + X_4

        self._VI                     = (X / 225.) * (2**16)
        self._VI[self._VI > (2**16)] = 2**16
        self._VI[~self._idx]         = 0.
        self._VI                     = self._VI.astype(uint16)
