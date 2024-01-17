import omero
import omero.cli
import omero.gateway
from omero.rtypes import rdouble, rint
from omero.model import RoiI, MaskI
from omero.gateway import ColorHolder
import numpy as np


dry_run = False


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
    mask_dataset_name = dataset.getName().replace("-", "_processed-")
    mask_image_name = f"cellOligomerPosition_{image.getName()}"
    mask_dataset = conn.getObject("Dataset", attributes={"name": mask_dataset_name})
    for mask_image in mask_dataset.listChildren():
        if mask_image.getName() == mask_image_name:
            return mask_image
    return None


def create_roi(mask_img):
    zct_list = []
    for t in range(0, mask_img.getSizeT()):
        zct_list.append((0, 0, t))
    planes = mask_img.getPrimaryPixels().getPlanes(zct_list)
    roi = omero.model.RoiI()
    for t, plane in enumerate(planes):
        mask = MaskI()
        mask.setBytes(np.packbits(np.asarray(plane, dtype=int)))
        #mask.setBytes(plane)
        mask.setWidth(rdouble(1200))
        mask.setHeight(rdouble(1200))
        mask.setX(rdouble(0))
        mask.setY(rdouble(0))
        mask.setTheT(rint(t))
        ch = ColorHolder.fromRGBA(255, 255, 0, 128)
        mask.setFillColor(rint(ch.getInt()))
        roi.addShape(mask)
    if roi.sizeOfShapes() > 0:
        return roi
    return None


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
        if not mask_image:
            print(f"No mask image found for {ds.getName()}/{img.getName()} !")
            continue

        roi = create_roi(mask_image)
        if not dry_run:
            save_roi(conn, img, roi)
            print(f"Mask added to {ds.getName()}/{img.getName()}.")
        else:
            print(f"Mask not added to {ds.getName()}/{img.getName()} (dry run)")
