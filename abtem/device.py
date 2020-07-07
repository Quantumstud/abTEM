from typing import Any

import mkl_fft
import numpy as np

from abtem.cpu_kernels import abs2, complex_exponential, interpolate_radial_functions, scale_reduce, \
    windowed_scale_reduce

# TODO : This is a little ugly, change after mkl_fft is updated

try:  # This should be the only place to get cupy, to make it a non-essential dependency
    import cupy as cp
    import cupyx.scipy.fft
    from abtem.cuda_kernels import launch_interpolate_radial_functions, launch_scale_reduce, \
        launch_windowed_scale_reduce

    get_array_module = cp.get_array_module


    def fft2_convolve(array, kernel, overwrite_x=True):
        array = cupyx.scipy.fft.fft2(array, overwrite_x=overwrite_x)
        array *= kernel
        array = cupyx.scipy.fft.ifft2(array, overwrite_x=overwrite_x)
        return array


    gpu_functions = {'fft2': cupyx.scipy.fft.fft2,
                     'ifft2': cupyx.scipy.fft.ifft2,
                     'fft2_convolve': fft2_convolve,
                     'complex_exponential': lambda x: cp.exp(1.j * x),
                     'abs2': lambda x: cp.abs(x) ** 2,
                     'interpolate_radial_functions': launch_interpolate_radial_functions,
                     'scale_reduce': launch_scale_reduce,
                     'windowed_scale_reduce': launch_windowed_scale_reduce}

    asnumpy = cp.asnumpy

except ImportError:
    cp = None
    get_array_module = lambda *args, **kwargs: np
    fft2_gpu = None
    ifft2_gpu = None
    fft2_convolve_gpu = None
    gpu_functions = {'fft2': None, 'ifft2': None, 'fft2_convolve': None}
    asnumpy = np.asarray


def fft2_convolve(array, kernel, overwrite_x=True):
    def _fft_convolve(array, kernel, overwrite_x):
        mkl_fft.fft2(array, overwrite_x=overwrite_x)
        array *= kernel
        mkl_fft.ifft2(array, overwrite_x=overwrite_x)
        return array

    if not overwrite_x:
        array = array.copy()

    if len(array.shape) == 2:
        return _fft_convolve(array, kernel, overwrite_x=True)
    elif (len(array.shape) == 3) & overwrite_x:
        for i in range(len(array)):
            _fft_convolve(array[i], kernel, overwrite_x=True)
        return array
    else:
        raise ValueError()


def fft2(array, overwrite_x):
    if not overwrite_x:
        array = array.copy()

    if len(array.shape) == 2:
        return mkl_fft.fft2(array, overwrite_x=True)
    elif (len(array.shape) == 3):
        for i in range(array.shape[0]):
            mkl_fft.fft2(array[i], overwrite_x=True)
        return array
    else:
        raise NotImplementedError()


def ifft2(array, overwrite_x):
    if len(array.shape) == 2:
        return mkl_fft.ifft2(array, overwrite_x=overwrite_x)
    elif len(array.shape) == 3:
        for i in range(array.shape[0]):
            array = mkl_fft.ifft2(array, overwrite_x=overwrite_x)
        return array
    else:
        raise NotImplementedError()


cpu_functions = {'fft2': fft2,
                 'ifft2': ifft2,
                 'fft2_convolve': fft2_convolve,
                 'abs2': abs2,
                 'complex_exponential': complex_exponential,
                 'interpolate_radial_functions': interpolate_radial_functions,
                 'scale_reduce': scale_reduce,
                 'windowed_scale_reduce': windowed_scale_reduce}


def get_device_function(xp, name):
    if xp is cp:
        return gpu_functions[name]
    elif xp is np:
        return cpu_functions[name]
    else:
        raise RuntimeError()


class HasDeviceMixin:
    _device_definition: Any

    @property
    def device_definition(self):
        return self._device_definition

    def set_device_definition(self, device_definition):
        self._device_definition = device_definition

    def get_array_module(self):
        if self.device_definition == 'cpu':
            return np

        if self.device_definition == 'gpu':
            if cp is None:
                raise RuntimeError('cupy is not installed, only cpu calculations available')
            return cp

        return get_array_module(self.device_definition)