import click as cli
import h5py
import yaml

from pathlib import Path



@cli.command(context_settings={"help_option_names": ["-h", "--help"], "show_default": True})
@cli.argument("vdir", type=cli.Path(exists=True, resolve_path=True, path_type=Path, file_okay=False))
@cli.option("--output-filename", "-o", "oname", default="processed-files.yml",
            type=cli.Path(resolve_path=True, path_type=Path),
            help="Where to store list of properly processed files.")
def check_if_processed(vdir, oname):
    """
    In the event of data pre-processing crashing, use this to list successfully
    processed files.

    \b
    VDIR    DIR    Directory of pre-processed files.
    """
    ok_files = []
    for vname in vdir.iterdir():
        try:
            vox = h5py.File(vname, 'r')
        except OSError: # File was probably not closed properly or something
            continue
        try:
            nbf = vox["FrameInfo"]["frameNumber"][()]
        except KeyError: # If this didn't get store, for sure the file is incomplete
            vox.close()
            continue
        vshape = vox["VolumeInfo"]["shape"][()]
        for f in range(nbf):
            try:
                vox["Input"][f"grid{f:02d}"][()].shape == vshape
                vox["GroundTruth"][f"grid{f:02d}"][()].shape == vshape
            except KeyError: # We're missing at least a grid
                vox.close()
                break
            if vox["GroundTruth"][f"grid{f:02d}"][()].sum() == 0:
                vox.close() # Ground truth is innexistant or didn't voxelize properly
                break
        if vox.id.valid: # Meaning file is still open
            ok_files.append(vname.stem)
            vox.close()
    with open(oname, 'w') as fd:
        yaml.dump(ok_files, fd, default_flow_style=False, indent=4)



if __name__ == "__main__":
    check_if_processed()
