"""
Based on code from Gabriel Kiss 01.2020
"""

import comtypes.client as ccomtypes
import numpy as np
import platform

from pathlib import WindowsPath
from warnings import filterwarnings

from preprocess.lookup_table import LUT
from preprocess.utils import safe2np, frame2arr




### Change this according to your system ###
Image3DAPIWin32 = None
Image3DAPIx64 = WindowsPath("C:/Users/malou/Documents/dev/Image3dAPI/x64/Image3dAPI.tlb")
############################################

# Silence a warning I can't do anything about
filterwarnings("ignore", message="A builtin ctypes object gave a PEP3118 format string that does not match its itemsize, so a best-guess will be made of the data type. Newer versions of python may behave correctly.")

# Patch for files that are not fully annotated
_PROBLEMATIC_CHILDS = { "104001": 19, "110001": 26, "470001": 18, "730001": 25, "920001": 31 }



def get_frames(src, hdf, bbox, max_vshape, fname):
    nbf = src.GetFrameCount() # Number of frames
    if fname.parent.stem in _PROBLEMATIC_CHILDS.keys():
        nbf = _PROBLEMATIC_CHILDS[fname.parent.stem]
        #nbf = 19 # Patch because that file isn't fully annotated
    try:
        # API returns unsigned int
        lut = np.array(src.GetColorMap(), dtype=np.uint).astype(np.uint8)
    except AttributeError:
        lut = LUT
    group = hdf.create_group("/Input")
    time = []
    for f in range(nbf):
        frame = src.GetFrame(f, bbox, max_vshape)
        arr_frame = lut[frame2arr(frame)]
        group.create_dataset(f"grid{f:02d}", data=arr_frame)
        time.append(frame.time)
    # Safely assume the same shape for every frame
    hdf["VolumeInfo"].create_dataset("shape", data=arr_frame.shape)
    group = hdf.create_group("/FrameInfo")
    group.create_dataset("frameNumber", data=int(nbf))
    group.create_dataset("frameTimes", data=np.array(time))


def dcm2vox(fname, hdf, vres):
    if "32" in platform.architecture()[0]:
        Image3dAPI = ccomtypes.GetModule(str(Image3DAPIWin32))
    else:
        Image3dAPI = ccomtypes.GetModule(str(Image3DAPIx64))
    # Create loader object
    loader = ccomtypes.CreateObject("GEHC_CARD_US.Image3dFileLoader")
    loader = loader.QueryInterface(Image3dAPI.IImage3dFileLoader)
    # Load file
    err_type, err_msg = loader.LoadFile(str(fname)) #TODO? Print errors
    src = loader.GetImageSource()
    # Get volume & various information
    ecg = src.GetECG()
    samples = safe2np(ecg.samples)
    trig_time = safe2np(ecg.trig_times)
    bbox = src.GetBoundingBox()
    origin = np.array([bbox.origin_x, bbox.origin_y, bbox.origin_z])
    dir_x = np.array([bbox.dir1_x, bbox.dir1_y, bbox.dir1_z])
    dir_y = np.array([bbox.dir2_x, bbox.dir2_y, bbox.dir2_z])
    dir_z = np.array([bbox.dir3_x, bbox.dir3_y, bbox.dir3_z])
    directions = np.stack([dir_x, dir_y, dir_z])
    vshape = np.round(np.linalg.norm(directions, axis=1) / vres)
    max_vshape = np.ctypeslib.as_ctypes(vshape.astype(np.ushort))
    # Store in HDF format
    group = hdf.create_group("/ECG")
    group.create_dataset("samples", data=samples)
    try:
        group.create_dataset("times", data=np.linspace(trig_time[0], trig_time[1],
                                                       num=samples.shape[0]))
    except IndexError: # No ECG timestamp find or just one, so skip
        group.create_dataset("times", dtype="float")
    group = hdf.create_group("/VolumeInfo")
    group.create_dataset("origin", data=origin)
    group.create_dataset("directions", data=directions)
    group.create_dataset("resolution", data=vres)
    group.create_dataset("colorMap", data=src.GetColorMap())
    get_frames(src, hdf, bbox, max_vshape, fname)
