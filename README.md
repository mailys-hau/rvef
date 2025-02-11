# Right Ventricle Ejection Fraction (RVEF)
Codebase for data processing & automatic segmentation of 3D right ventricle on ultrasound, with the goal of computing its ejection fraction automatically.

## Preprocessing
The preprocessing script will fetch various elements and aggregate them in a single HDF file per acquisition. Mainly, the script will convert DICOMs and meshes to voxel, and align the meshe's voxel grid to the one from the corresponding DICOM. DICOMs will create the input voxel grid of your neural network, and meshes will be the ground truth (or segmentation mask). You can specify the paths to the information and volumes directories if you have them (see `-v` and `-i` options), which will store the right ventricle volume of each frame (from the mesh), as well as the end of the systole and diastole timestamp in the HDF.

<ins>**NB:**</ins>
- You will need a Windows machine with [Image3DAPI](https://github.com/MedicalUltrasound/Image3dAPI) installed to read the DICOMs.
- This process is _very time-consuming_, as we have to iterate through every voxel of the ground truth grid (i.e. mesh) to align it with the input (i.e. DICOM). If, by some bad luck, your voxelization process crashes, use `preprocess/double-check.py` to get the list of properly voxelized files in a YAML file, and give that YAML file to the preprocessing script using `--exclude-files` to not voxelize files twice.
- As we work with 4D data (3D over time) the **generated files are heavy**, so plan accordingly.

Hereinafter is the help command of the preprocessing script:
```
$ python preprocessing.py --help
Usage: preprocessing.py [OPTIONS] DCMDIR PLYDIR

  Convert GE DICOMs 3D volumes and 3D mesh to voxel grids. Store everything in an HDF.

  DCMDIR    PATH    Directory of DICOMs input to convert to voxels.
  PLYDIR    PATH    Directory of PLYs output to convert to voxels.

Options:
  -v, --volumes-directory PATH    Directory of CSVs with the blood volume for each frame.
  -i, --information-directory PATH
                                  Directory of information about ED & ES time frame.
  -r, --voxel-resolution <FLOAT RANGE FLOAT RANGE FLOAT RANGE>...
                                  Voxel spacing in meter.  [default: 0.0005, 0.0005, 0.0005]
  -o, --output-directory PATH     Where to store generated voxel grids.  [default: voxel-grids]
  -e, --exclude-files FILE        List of file to exclude from pre-processing. If given, must be a YAML file.
  -n, --number-workers INTEGER RANGE
                                  Number of worker used to accelerate file processing.  [default: 1; x>=1]
  -h, --help                      Show this message and exit.  [default: False]
```

## Data
Each file the aggregated dataset, using `preprocessing.py` follow the below structure:
```
.
├── ECG/
│   ├── samples
│   └── times
├── FrameInfo/
│   ├── endDiastole
│   ├── endSystole
│   ├── frameNumber
│   └── frameTimes
├── GroundTruth/
│   ├── grid00
│   ├── grid01
│   └── ...
├── Input/
│   ├── grid00
│   ├── grid01
│   └── ...
└── VolumeInfo/
    ├── colorMap
    ├── directions
    ├── origin
    ├── resolution
    ├── shape
    └── volumes
```
