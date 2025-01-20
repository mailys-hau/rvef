import click as cli

from pathlib import WindowsPath
from subprocess import run



def _get_smallest(directory):
    """ Return filename of smallest file in directory """
    out = next(directory.iterdir())
    for fname in directory.iterdir():
        if fname.suffix in [".json", ".csv", ".ply"] or fname.is_dir():
            continue
        if fname.stat().st_size < out.stat().st_size:
            out = fname
    return out

def _get_other(other):
    """ Return the first filename that is different than other in the same directory """
    out = other
    for fname in other.parent.iterdir():
        if fname.suffix in [".json", ".csv", ".ply"] or fname.is_dir() or fname.name == other.name:
            continue
        return fname


# Add flag to extract mesh, ed, es, volume
@cli.command(context_settings={"help_option_names": ["-h", "--help"], "show_default": True})
@cli.argument("pdcm", type=cli.Path(exists=True, resolve_path=True, file_okay=False, path_type=WindowsPath))
@cli.option("--output-directory", "-o", "pout", type=cli.Path(resolve_path=True, path_type=WindowsPath),
            default="outputs", help="Where output files will be stored.")
@cli.option("--mesh/--no-mesh", "-m/-M", default=True,
            help="Whether to extract right ventricle meshes.")
@cli.option("--end-diastole/--no-end-diastole", "-d/-D", "ed", default=False,
            help="Whether to extract end diastole mesh.")
@cli.option("--end-systole/--no-end-systole", "-s/-S", "es", default=False,
            help="Whether to extract end systole mesh.")
@cli.option("--volume/--no-volume", "-v/-V", default=True,
            help="Whether to extract volumes for each right ventricle meshes.")
def extract_mesh(pdcm, pout, mesh, ed, es, volume):
    """
    Extract meshes from AutoRVQ using the `PersistentStateLoader.exe` from GE. This
    script must be located in the same place as `PersistentStateLoader.exe`.
    The DICOM files must be organised as followed:
    \b
    PDCM/
    |-- subdir/
        |-- input
        |-- input_with_autoRVQ_state
    |-- subdir2/
        |-- ...

    /!\ For some reason, ED & ES can't be extracted at the same time as all meshes. Just run the script twice...

    PDCM    DIR    Directory where the data to be extracted is located
    """
    pout.mkdir(parents=True, exist_ok=True)
    for fname in pdcm.iterdir():
        if not fname.is_dir():
            continue
        rvname = _get_smallest(fname) #Try this first, because it's the most likely
        print(f"Extracting file {WindowsPath().joinpath(rvname.parent.name, rvname.name)}. . .")
        oname = pout.joinpath(fname.name)
        oname.mkdir(parents=True, exist_ok=True)
        # Convert flag to string arguments
        mesh = "--mesh" if mesh else ''
        ed = "--ed" if ed else ''
        es = "--es" if es else ''
        volume = "--volume" if volume else ''
        res = run(["PersistentStateLoader.exe", f"{rvname}", f"{oname}", f"{mesh}",
                   f"{ed}", f"{es}", f"{volume}"], stdout=None)
        if res.returncode != 0: # There was an issue with the file
            # Try the other DICOM in the directory
            rvname = _get_other(rvname)
            print(f"Whoops, looked at the wrong file. Extracting {WindowsPath().joinpath(rvname.parent.name, rvname.name)}. . .")
            res = run(["PersistentStateLoader.exe", f"{rvname}", f"{oname}",
                       f"{mesh}", f"{ed}", f"{es}", f"{volume}"], stdout=None)



if __name__ == "__main__":
    extract_mesh()
