import click as cli
import h5py
import json
import numpy as np
import pandas as pd
import yaml

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from pathlib import WindowsPath

from preprocess import dcm2vox, ply2vox
from utils.progress import NestedProgress



def _get_dcm_name(mpath, dcm): #FIXME: Dunno if this is correct
    mname = next(mpath.glob("*.ply")).stem.split('_')[0]
    for dname in dcm.iterdir():
        if dname.stem != mname:
            return dname # If it has the same name as mesh, then it's EchoPAC annotation

def file2vox(dcm, plydir, voldir, infodir, vres, opath, progress, tid):
    nmesh = len(list(plydir.iterdir()))
    if not dcm.is_dir():
        progress[tid] = { "progress": nmesh, "total": nmesh }
        return
    mpath = plydir.joinpath(dcm.name)
    # There's several dicom associated to the patient, we make sure to get the correct one
    dname = _get_dcm_name(mpath, dcm)
    hdf = h5py.File(opath.joinpath(mpath.name).with_suffix(".h5"), 'w')
    dcm2vox(dname, hdf, vres) # Input 3D images
    ply2vox(mpath, hdf, progress, tid) # Ground truth 3D mesh
    # Add volumes + ES & ED frame number and time
    if voldir is not None:
        vol = pd.read_csv(next(voldir.joinpath(mpath.name).glob("*_volume.csv")))
        hdf["VolumeInfo"].create_dataset("volumes", data=vol.volume)
    if infodir is not None:
        with open(next(infodir.joinpath(mpath.name).glob("*.json")), 'r') as fd:
            key_frames = json.load(fd)["segmentation_stage"]["key_frames_time"]
        # Storing only timestamp is sufficient
        hdf["FrameInfo"].create_dataset("endDiastole", data=key_frames["ed"])
        hdf["FrameInfo"].create_dataset("endSystole", data=key_frames["es"])
    hdf.close()



@cli.command(context_settings={"help_option_names": ["--help", "-h"], "show_default": True})
@cli.argument("dcmdir", type=cli.Path(exists=True, resolve_path=True, path_type=WindowsPath))
@cli.argument("plydir", type=cli.Path(exists=True, resolve_path=True, path_type=WindowsPath))
@cli.option("--volumes-directory", "-v", "voldir",
            type=cli.Path(exists=True, resolve_path=True, path_type=WindowsPath),
            help="Directory of CSVs with the blood volume for each frame.")
@cli.option("--information-directory", "-i", "infodir",
            type=cli.Path(exists=True, resolve_path=True, path_type=WindowsPath),
            help="Directory of information about ED & ES time frame.")
@cli.option("--voxel-resolution", "-r", "vres", type=cli.Tuple([cli.FloatRange(min=0)] * 3),
            nargs=3, default=[0.0005] * 3, help="Voxel spacing in meter.")
@cli.option("--output-directory", "-o", "opath", default="voxel-grids",
            type=cli.Path(resolve_path=True, path_type=WindowsPath),
            help="Where to store generated voxel grids.")
@cli.option("--exclude-files", "-e", "exclude",
            type=cli.Path(exists=True, dir_okay=False, resolve_path=True, path_type=WindowsPath),
            help="List of file to exclude from pre-processing. If given, must be a YAML file.")
@cli.option("--number-workers", "-n", "nb_workers", default=1, type=cli.IntRange(min=1),
            help="Number of worker used to accelerate file processing.")
def data2hdf(dcmdir, plydir, voldir, infodir, vres, opath, exclude, nb_workers):
    """
    Convert GE DICOMs 3D volumes and 3D mesh to voxel grids. Store everything in an HDF.

    \b
    DCMDIR    PATH    Directory of DICOMs input to convert to voxels.
    PLYDIR    PATH    Directory of PLYs output to convert to voxels.
    """
    opath.mkdir(exist_ok=True)
    vres = np.array(vres)
    if exclude is not None:
        with open(exclude, 'r') as fd:
            exclude = yaml.safe_load(fd)
    else:
        exclude = []
    with NestedProgress() as prb:
        # Original code for multiprocessing:
        # https://www.deanmontgomery.com/2022/03/24/rich-progress-and-multiprocessing/
        futures = [] # Keep track of jobs
        with Manager() as manager:
            _progress = manager.dict()
            tid1 = prb.add_task("Processing", progress_type="patient")
            with ProcessPoolExecutor(max_workers=nb_workers) as executor:
                for dcm in dcmdir.iterdir():
                    if dcm.stem in exclude:
                        continue
                    # `visible` to False to not pollute output (only show on going voxelization)
                    tid2 = prb.add_task(f"Voxelizing {dcm.name}", visible=False, progress_type="voxel")
                    futures.append(executor.submit(file2vox, dcm, plydir, voldir, infodir,
                                                   vres, opath, _progress, tid2))
                # Monitor the progress
                while (n_done := sum([f.done() for f in futures])) < len(futures):
                    prb.update(tid1, completed=n_done, total=len(futures))
                    for tid, update_data in _progress.items():
                        latest = update_data["progress"]
                        tot = update_data["total"]
                        prb.update(tid, completed=latest, total=tot, visible=(latest<tot))
                for future in futures:
                    future.result() # Raise any encountered errors



if __name__ == "__main__":
    data2hdf()
