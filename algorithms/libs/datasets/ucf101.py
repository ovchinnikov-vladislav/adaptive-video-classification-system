import urllib.request
import os
import patoolib
import pandas as pd
import numpy as np
import math
import libs.datasets.utls as utils


def __download_ucf101(data_dir_path):
    ucf_rar = os.path.join(data_dir_path, 'UCF101.rar')

    url_link = 'https://crcv.ucf.edu/data/UCF101/UCF101.rar'

    if not os.path.exists(data_dir_path):
        os.makedirs(data_dir_path)

    if not os.path.exists(ucf_rar):
        print('ucf file does not exist, downloading from Internet')
        urllib.request.urlretrieve(url=url_link, filename=ucf_rar,
                                   reporthook=utils.reporthook)

    print('unzipping ucf file')
    patoolib.extract_archive(ucf_rar, outdir=data_dir_path)


def __scan_ucf101(data_dir_path, limit):
    input_data_dir_path = os.path.join(data_dir_path, 'UCF-101')

    result = dict()

    dir_count = 0
    for f in os.listdir(input_data_dir_path):
        __help_scan_ucf101(input_data_dir_path, f, dir_count, result)
        if dir_count == limit:
            break
    return result


def __help_scan_ucf101(input_data_dir_path, f, dir_count, result):
    file_path = os.path.join(input_data_dir_path, f)
    if not os.path.isfile(file_path):
        dir_count += 1
        for ff in os.listdir(file_path):
            video_file_path = os.path.join(file_path, ff)
            result[video_file_path] = f


def __scan_ucf101_with_labels(data_dir_path, labels):
    input_data_dir_path = os.path.join(data_dir_path, 'UCF-101')

    result = dict()

    dir_count = 0
    for label in labels:
        __help_scan_ucf101(input_data_dir_path, label, dir_count, result)
    return result


def download_data(data_dist_path, image_width=250, image_height=250, image_gray=False):
    ucf101_data_dir_path = os.path.join(data_dist_path, "UCF-101")
    if not os.path.exists(ucf101_data_dir_path):
        __download_ucf101(data_dist_path)

    videos = []
    labels = []
    name_class_labels = dict()

    dir_count = 0
    for f in os.listdir(ucf101_data_dir_path):
        file_path = os.path.join(ucf101_data_dir_path, f)
        print(file_path)
        if not os.path.isfile(file_path):
            dir_count += 1
            for video in os.listdir(file_path):
                videos.append(os.path.join(file_path, video))
                labels.append(dir_count - 1)
                name_class_labels[dir_count - 1] = f

    videos = pd.DataFrame(videos, labels).reset_index()
    videos.columns = ["labels", "video_name"]
    videos.groupby('labels').count()

    train_set = pd.DataFrame()
    test_set = pd.DataFrame()
    for i in set(labels):
        vs = videos.loc[videos["labels"] == i]
        vs_range = np.arange(len(vs))
        np.random.seed(12345)
        np.random.shuffle(vs_range)

        vs = vs.iloc[vs_range]
        last_train = len(vs) - len(vs) // 3
        train_vs = vs.iloc[:last_train]
        train_set = train_set.append(train_vs)
        test_vs = vs.iloc[last_train:]
        test_set = test_set.append(test_vs)

    train_set = train_set.reset_index().drop("index", axis=1)
    test_set = test_set.reset_index().drop("index", axis=1)

    train_videos_dir = os.path.join(ucf101_data_dir_path, "UCF101_Frames")
    test_videos_dir = os.path.join(ucf101_data_dir_path, "UCF101_Frames")
    try:
        os.rmdir(train_videos_dir)
    except FileNotFoundError as e:
        print(train_videos_dir + " not exists, then create")
    os.mkdir(train_videos_dir)
    try:
        os.rmdir(test_videos_dir)
    except FileNotFoundError as e:
        print(test_videos_dir + " not exists, then create")
    os.mkdir(test_videos_dir)

    utils.video_capturing_function(ucf101_data_dir_path, train_set, "UCF101_Frames", image_width, image_height, image_gray, name_class_labels)
    utils.video_capturing_function(ucf101_data_dir_path, test_set, "UCF101_Frames", image_width, image_height, image_gray, name_class_labels)


def load_dataset(data_dist_path, frame_size=10, image_width=250, image_height=250):
    ucf101_data_dir_path = os.path.join(data_dist_path, "UCF-101")
    if not os.path.exists(ucf101_data_dir_path):
        __download_ucf101(data_dist_path)

    videos = []
    labels = []
    name_class_labels = dict()

    dir_count = 0
    for f in os.listdir(ucf101_data_dir_path):
        file_path = os.path.join(ucf101_data_dir_path, f)
        print(file_path)
        if not os.path.isfile(file_path):
            dir_count += 1
            for video in os.listdir(file_path):
                videos.append(os.path.join(file_path, video))
                labels.append(dir_count - 1)
                name_class_labels[dir_count - 1] = f

    videos = pd.DataFrame(videos, labels).reset_index()
    videos.columns = ["labels", "video_name"]
    videos.groupby('labels').count()

    train_set = pd.DataFrame()
    test_set = pd.DataFrame()
    for i in set(labels):
        vs = videos.loc[videos["labels"] == i]
        vs_range = np.arange(len(vs))
        np.random.seed(12345)
        np.random.shuffle(vs_range)

        vs = vs.iloc[vs_range]
        last_train = len(vs) - len(vs) // 3
        train_vs = vs.iloc[:last_train]
        train_set = train_set.append(train_vs)
        test_vs = vs.iloc[last_train:]
        test_set = test_set.append(test_vs)

    train_set = train_set.reset_index().drop("index", axis=1)
    test_set = test_set.reset_index().drop("index", axis=1)

    train_videos_dir = os.path.join(ucf101_data_dir_path, "Trains")
    test_videos_dir = os.path.join(ucf101_data_dir_path, "Tests")
    try:
        os.rmdir(train_videos_dir)
    except FileNotFoundError as e:
        print(train_videos_dir + " not exists, then create")
    os.mkdir(train_videos_dir)
    try:
        os.rmdir(test_videos_dir)
    except FileNotFoundError as e:
        print(test_videos_dir + " not exists, then create")
    os.mkdir(test_videos_dir)

    utils.video_capturing_function(ucf101_data_dir_path, train_set, "Trains")
    utils.video_capturing_function(ucf101_data_dir_path, test_set, "Tests")

    train_frames = []
    for i in np.arange(len(train_set.video_name)):
        vid_file_name = os.path.basename(train_set.video_name[i]).split(".")[0]
        train_frames.append(len(os.listdir(os.path.join(train_videos_dir, vid_file_name))))

    test_frames = []
    for i in np.arange(len(test_set.video_name)):
        vid_file_name = os.path.basename(test_set.video_name[i]).split('.')[0]
        test_frames.append(len(os.listdir(os.path.join(test_videos_dir, vid_file_name))))

    utils.frame_generating_function(train_set, train_videos_dir, frame_size=frame_size)
    utils.frame_generating_function(test_set, test_videos_dir, frame_size=frame_size)

    train_vid_dat = pd.DataFrame()
    validation_vid_dat = pd.DataFrame()
    for label in set(labels):
        label_dat = train_set.loc[train_set["labels"] == label]
        train_len_label = math.floor(len(label_dat) * 0.80)

        train_dat_label = label_dat.iloc[:train_len_label]
        validation_dat_label = label_dat.iloc[train_len_label:]

        train_vid_dat = train_vid_dat.append(train_dat_label, ignore_index=True)
        validation_vid_dat = validation_vid_dat.append(validation_dat_label, ignore_index=True)

    train_dataset = utils.data_load_function_frames(train_vid_dat, train_videos_dir,
                                                    frame_size=frame_size,
                                                    image_width=image_width,
                                                    image_height=image_height)
    test_dataset = utils.data_load_function_frames(test_set, test_videos_dir,
                                                   frame_size=frame_size,
                                                   image_width=image_width,
                                                   image_height=image_height)
    validation_dataset = utils.data_load_function_frames(validation_vid_dat, train_videos_dir,
                                                         frame_size=frame_size,
                                                         image_width=image_width,
                                                         image_height=image_height)

    train_labels = np.array(train_vid_dat.labels)
    test_labels = np.array(test_set.labels)
    validation_labels = np.array(validation_vid_dat.labels)

    return (train_dataset, train_labels), (test_dataset, test_labels), (validation_dataset, validation_labels)


if __name__ == '__main__':
    download_data(os.path.join('D:' + os.path.sep + 'tensorflow_datasets', 'UCF-101'), 160, 120)
