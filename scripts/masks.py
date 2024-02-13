import omero
import omero.cli
import omero.gateway
from omero.rtypes import rdouble, rint
from omero.model import RoiI, MaskI
from omero.gateway import ColorHolder
import numpy as np
from skimage.io import imread

dry_run = False

MASK_PATH = "/uod/idr/filesets/idr0155-fu-alphasynuclein/microglia_oligomer_processed/<PATIENT>/cellOligomerPosition_<IMAGE_NAME>"

def get_images(conn):
    """
    Get all images of the idr0144 project
    :param conn: omero connection
    :return: Generator
    """
    project = conn.getObject("Project", attributes={"name": "idr0155-fu-alphasynuclein/experimentA"})
    for dataset in project.listChildren():
        if "processed" in dataset.getName():
            continue
        for image in dataset.listChildren():
            yield dataset, image


def get_mask_image(conn, dataset, image):
    patient = ds.getName().replace("microglia_oligomer-", "")
    path = MASK_PATH.replace("<PATIENT>", patient)
    path = path.replace("<IMAGE_NAME>", image.getName())
    try:
        return imread(path)
    except Exception as e:
        print(f"Can't read {path}: {e}")
    return None


def create_roi(mask_img):
    roi = omero.model.RoiI()
    for t in range(0, mask_img.shape[0]):
        mask = MaskI()
        mask.setBytes(np.packbits(np.asarray(mask_img[t], dtype=int)))
        mask.setWidth(rdouble(1200))
        mask.setHeight(rdouble(1200))
        mask.setX(rdouble(0))
        mask.setY(rdouble(0))
        mask.setTheT(rint(t))
        ch = ColorHolder.fromRGBA(255, 255, 0, 128)
        mask.setFillColor(rint(ch.getInt()))
        roi.addShape(mask)
    return roi


def save_roi(conn, img, roi):
    us = conn.getUpdateService()
    roi.setImage(img._obj)
    us.saveAndReturnObject(roi)


def delete_rois(conn, im):
    """
    Delete all ROIs attached to the given image
    :param conn: omero connection
    :param im: The image
    :return: Nothing
    """
    result = conn.getRoiService().findByImage(im.id, None)
    to_delete = []
    for roi in result.rois:
        to_delete.append(roi.getId().getValue())
    if to_delete:
        conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


with omero.cli.cli_login() as c:
    conn = omero.gateway.BlitzGateway(client_obj=c.get_client())

    for ds, img in get_images(conn):
        if not dry_run:
            delete_rois(conn, img)

        mask_image = get_mask_image(conn, ds, img)
        if mask_image is None:
            print(f"No mask image found for {ds.getName()}/{img.getName()} !")
            continue

        roi = create_roi(mask_image)
        if not dry_run:
            save_roi(conn, img, roi)
            print(f"Mask added to {ds.getName()}/{img.getName()}.")
        else:
            print(f"Mask not added to {ds.getName()}/{img.getName()} (dry run)")
