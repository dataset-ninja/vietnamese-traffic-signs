import os
import shutil
from urllib.parse import unquote, urlparse

import supervisely as sly
from dataset_tools.convert import unpack_if_archive
from supervisely.io.fs import file_exists, get_file_name
from tqdm import tqdm

import src.settings as s


def download_dataset(teamfiles_dir: str) -> str:
    """Use it for large datasets to convert them on the instance"""
    api = sly.Api.from_env()
    team_id = sly.env.team_id()
    storage_dir = sly.app.get_data_dir()

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, str):
        parsed_url = urlparse(s.DOWNLOAD_ORIGINAL_URL)
        file_name_with_ext = os.path.basename(parsed_url.path)
        file_name_with_ext = unquote(file_name_with_ext)

        sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
        local_path = os.path.join(storage_dir, file_name_with_ext)
        teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

        fsize = api.file.get_directory_size(team_id, teamfiles_dir)
        with tqdm(
            desc=f"Downloading '{file_name_with_ext}' to buffer...",
            total=fsize,
            unit="B",
            unit_scale=True,
        ) as pbar:
            api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)
        dataset_path = unpack_if_archive(local_path)

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, dict):
        for file_name_with_ext, url in s.DOWNLOAD_ORIGINAL_URL.items():
            local_path = os.path.join(storage_dir, file_name_with_ext)
            teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

            if not os.path.exists(get_file_name(local_path)):
                fsize = api.file.get_directory_size(team_id, teamfiles_dir)
                with tqdm(
                    desc=f"Downloading '{file_name_with_ext}' to buffer...",
                    total=fsize,
                    unit="B",
                    unit_scale=True,
                ) as pbar:
                    api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)

                sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
                unpack_if_archive(local_path)
            else:
                sly.logger.info(
                    f"Archive '{file_name_with_ext}' was already unpacked to '{os.path.join(storage_dir, get_file_name(file_name_with_ext))}'. Skipping..."
                )

        dataset_path = storage_dir
    return dataset_path


def count_files(path, extension):
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(extension):
                count += 1
    return count


def convert_and_upload_supervisely_project(
    api: sly.Api, workspace_id: int, project_name: str
) -> sly.ProjectInfo:
    ### Function should read local dataset and upload it to Supervisely project, then return project info.###
    images_path = "/home/alex/DATASETS/TODO/Vietnamese_traffic_signs/archive/train_data/images"
    bboxes_path = "/home/alex/DATASETS/TODO/Vietnamese_traffic_signs/archive/train_data/labels"
    images_ext = ".png"
    ann_ext = ".txt"
    batch_size = 30

    def create_ann(image_path):
        labels = []

        image_np = sly.imaging.image.read(image_path)[:, :, 0]
        img_height = image_np.shape[0]
        img_wight = image_np.shape[1]

        bbox_path = os.path.join(curr_bboxes_path, get_file_name(image_path) + ann_ext)

        if file_exists(bbox_path):
            with open(bbox_path) as f:
                content = f.read().split("\n")

                for curr_data in content:
                    if len(curr_data) != 0:
                        curr_data = list(map(float, curr_data.split(" ")))
                        obj_class = idx_to_class.get(int(curr_data[0]))

                        left = int((curr_data[1] - curr_data[3] / 2) * img_wight)
                        right = int((curr_data[1] + curr_data[3] / 2) * img_wight)
                        top = int((curr_data[2] - curr_data[4] / 2) * img_height)
                        bottom = int((curr_data[2] + curr_data[4] / 2) * img_height)
                        rectangle = sly.Rectangle(top=top, left=left, bottom=bottom, right=right)
                        label = sly.Label(rectangle, obj_class)
                        labels.append(label)

        return sly.Annotation(img_size=(img_height, img_wight), labels=labels)

    idx_to_class = {
        0: sly.ObjClass("one way prohibition", sly.Rectangle),
        1: sly.ObjClass("no parking", sly.Rectangle),
        2: sly.ObjClass("no stopping and parking", sly.Rectangle),
        3: sly.ObjClass("no turn left", sly.Rectangle),
        4: sly.ObjClass("no turn right", sly.Rectangle),
        5: sly.ObjClass("no u turn", sly.Rectangle),
        6: sly.ObjClass("no u and left turn", sly.Rectangle),
        7: sly.ObjClass("no u and right turn", sly.Rectangle),
        8: sly.ObjClass("no motorbike entry/turning", sly.Rectangle),
        9: sly.ObjClass("no car entry/turning", sly.Rectangle),
        10: sly.ObjClass("no truck entry/turning", sly.Rectangle),
        11: sly.ObjClass("other prohibition", sly.Rectangle),
        12: sly.ObjClass("indication", sly.Rectangle),
        13: sly.ObjClass("direction", sly.Rectangle),
        14: sly.ObjClass("speed limit", sly.Rectangle),
        15: sly.ObjClass("weight limit", sly.Rectangle),
        16: sly.ObjClass("height limit", sly.Rectangle),
        17: sly.ObjClass("pedestrian crossing", sly.Rectangle),
        18: sly.ObjClass("intersection danger", sly.Rectangle),
        19: sly.ObjClass("road danger", sly.Rectangle),
        20: sly.ObjClass("pedestrian danger", sly.Rectangle),
        21: sly.ObjClass("construction danger", sly.Rectangle),
        22: sly.ObjClass("slow warning", sly.Rectangle),
        23: sly.ObjClass("other warning", sly.Rectangle),
        24: sly.ObjClass("vehicle permission lane", sly.Rectangle),
        25: sly.ObjClass("vehicle and speed permission lane", sly.Rectangle),
        26: sly.ObjClass("overpass route", sly.Rectangle),
        27: sly.ObjClass("no more prohibition", sly.Rectangle),
        28: sly.ObjClass("other", sly.Rectangle),
    }

    project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
    meta = sly.ProjectMeta(obj_classes=list(idx_to_class.values()))
    api.project.update_meta(project.id, meta.to_json())

    for ds_name in ["train", "val", "test"]:
        dataset = api.dataset.create(project.id, ds_name, change_name_if_conflict=True)

        curr_images_path = os.path.join(images_path, ds_name)
        curr_bboxes_path = os.path.join(bboxes_path, ds_name)
        images_names = os.listdir(curr_images_path)

        progress = sly.Progress("Create dataset {}".format(ds_name), len(images_names))

        for images_names_batch in sly.batched(images_names, batch_size=batch_size):
            img_pathes_batch = [
                os.path.join(curr_images_path, image_name) for image_name in images_names_batch
            ]

            img_infos = api.image.upload_paths(dataset.id, images_names_batch, img_pathes_batch)
            img_ids = [im_info.id for im_info in img_infos]

            anns = [create_ann(image_path) for image_path in img_pathes_batch]
            api.annotation.upload_anns(img_ids, anns)

            progress.iters_done_report(len(images_names_batch))

    return project
