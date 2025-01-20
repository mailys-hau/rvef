"""
Code from Gabriel Kiss 01.2020
"""

import comtypes
import ctypes
import numpy as np



def safe2np(safearr_ptr, copy=True):
    """ Convert a SAFEARRAY buffer to its numpy equivalent """
    # Only support 1D data for now
    assert(comtypes._safearray.SafeArrayGetDim(safearr_ptr) == 1)
    # Access underlying pointer
    data_ptr = ctypes.POINTER(safearr_ptr._itemtype_)()
    comtypes._safearray.SafeArrayAccessData(safearr_ptr, ctypes.byref(data_ptr))
    # +1 to go from inclusive to exclusive bound
    upper_bound = comtypes._safearray.SafeArrayGetUBound(safearr_ptr, 1) + 1
    lower_bound = comtypes._safearray.SafeArrayGetLBound(safearr_ptr, 1)
    array_size = upper_bound - lower_bound
    # Wrap pointer in numpy array
    arr = np.ctypeslib.as_array(data_ptr, shape=(array_size,))
    return np.copy(arr) if copy else arr

def frame2arr(frame):
    arr1d = safe2np(frame.data, copy=False)
    assert(arr1d.dtype == np.uint8) # Only tested with 1 byte element
    arr3d = np.lib.stride_tricks.as_strided(arr1d, shape=frame.dims,
                                            strides=(1, frame.stride0, frame.stride1))
    return np.copy(arr3d)
