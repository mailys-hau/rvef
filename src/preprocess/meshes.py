"""
Code from github.com/mailys-hau/echovox
"""

import scipy.ndimage as sci
import numpy as np
import trimesh as tm
import trimesh.exchange.ply as tmply

from trimesh.voxel.creation import local_voxelize



def full_load_ply(file_obj, resolver=None, fix_texture=True, prefer_color=None,
                  *args, **kwargs):
    """ Trimesh's `load_ply` doesn't return normals, we're fixing this """
    # First part is the same as `trimesh.exchange.ply.load_ply`
    elements, is_ascii, image_name = tmply._parse_header(file_obj)
    if is_ascii:
        tmply._ply_ascii(elements, file_obj)
    else:
        tmply._ply_binary(elements, file_obj)
    image = None
    try:
        import PIL.Image
        if image_name is not None:
            data = resolver.get(image_name)
            image = PIL.Image.open(tm.util.wrap_as_stream(data))
    except ImportError:
        tm.util.log.debug("textures require `pip install pillow`")
    except BaseException:
        tm.util.log.warning("unable to load image!", exc_info=True)
    kwargs = tmply._elements_to_kwargs(
            image=image, elements=elements, fix_texture=fix_texture, prefer_color=prefer_color)
    # Check elements for normals and add it to the kwargs
    if "normal" in elements and elements["normal"]["length"]:
        normals = np.column_stack([elements["normal"]["data"][i] for i in "xyz"])
        if not tm.util.is_shape(normals, (-1, 3)):
            raise ValueError("Normals were not (n, 3)!")
        if normals.shape == kwargs["vertices"].shape:
            k = "vertex_normals"
        elif normals.shape[0] == kwargs["faces"].shape[0]:
            k = "face_normals"
        else:
            raise ValueError("Number of normals match neither vertices or faces!")
        kwargs[k] = normals
    return kwargs


def get_smallest_bounds(mesh, origin, delta):
    """
    Convert the mesh to the destination world before getting its bounding box.
    That way the bounding box is smaller than converting the bounding to the
    destination coordinate system.
    """
    # Mesh vertices in the voxel grid coordinate system
    def _get_coord(p):
        return np.linalg.inv(delta) @ (p - origin)
    vfunc = np.vectorize(_get_coord, signature="(n)->(n)")
    idx = vfunc(mesh.vertices)
    bbox = tm.Trimesh(vertices=abs(idx), faces=mesh.faces).bounds
    return bbox.astype(int)

def mesh2vox(hdf, mesh):
    """
    """
    vshape = hdf["VolumeInfo"]["shape"][()]
    vres = hdf["VolumeInfo"]["resolution"][()]
    origin = hdf["VolumeInfo"]["origin"][()]
    directions = hdf["VolumeInfo"]["directions"][()]
    delta = vres * directions / np.linalg.norm(directions, axis=0)
    grid = np.zeros(vshape, dtype=bool)
    bbox = get_smallest_bounds(mesh, origin, delta)
    for i in range(bbox[0, 0], bbox[1, 0] + 1):
        for j in range(bbox[0, 1], bbox[1, 1] + 1):
            for k in range(bbox[0, 2], bbox[1, 2] + 1):
                # This is highly ineficient, but that's the best choice we had to
                # align the input & ground truth
                idx = np.array([i, j, k])
                coord = delta.T @ idx + origin
                if mesh.contains(np.expand_dims(coord, axis=0)):
                    grid[i, j, k] = True
    return grid


def ply2vox(plydir, hdf, progress, tid):
    nbf = hdf["FrameInfo"]["frameNumber"][()]
    group = hdf.create_group("/GroundTruth")
    for i in range(nbf):
        fname = next(plydir.glob(f"*_{i:03d}.ply")) # Make sure it's ordered
        with open(fname, "br") as fd: # Need to be opened in binary mode for Trimesh
            dict_mesh = full_load_ply(fd, prefer_color="face")
        mesh = tm.Trimesh(**dict_mesh)
        grid = np.zeros(hdf["VolumeInfo"]["shape"][()], dtype=bool) #mesh2vox(hdf, mesh)
        group.create_dataset(f"grid{i:02d}", data=grid)
        progress[tid] = { "progress": i + 1, "total": nbf }
