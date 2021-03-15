from tensorflow.keras.layers import Input, Lambda
from tensorflow.keras.models import Model
from bmstu.yolo3.layers import yolo_body
from bmstu.yolo3.losses import yolo_loss
from bmstu.yolo3.utils import preprocess_true_boxes, get_random_data
import numpy as np


def get_classes(classes_path):
    with open(classes_path) as file:
        class_names = file.readlines()
    class_names = [c.strip() for c in class_names]
    return class_names


def get_anchors(anchors_path):
    with open(anchors_path) as file:
        anchors = file.readline()
    anchors = [float(x) for x in anchors.split(',')]
    return np.array(anchors).reshape(-1, 2)


def create_model(input_shape, anchors, num_classes, load_pretrained=True, freeze_body=2,
                 weights_path='model_data/yolo_weights.h5'):
    """create the training model"""
    image_input = Input(shape=(None, None, 3))
    h, w = input_shape
    num_anchors = len(anchors)

    y_true = [Input(shape=(h // {0: 32, 1: 16, 2: 8}[i], w // {0: 32, 1: 16, 2: 8}[i],
                           num_anchors // 3, num_classes + 5)) for i in range(3)]

    model_body = yolo_body(image_input, num_anchors // 3, num_classes)
    print('Create YOLOv3 model with {} anchors and {} num_classes.'.format(num_anchors, num_classes))

    # if load_pretrained:
    #     model_body.load_weights(weights_path, by_name=True, skip_mismatch=True)
    #     print('Load weights {}.'.format(weights_path))
    #     if freeze_body in [1, 2]:
    #         # Freeze darknet53 body or freeze all but 3 output layers.
    #         num = (185, len(model_body.layers) - 3)[freeze_body - 1]
    #         for i in range(num):
    #             model_body.layers[i].trainable = False
    #         print('Freeze the first {} layers of total {} layers.'.format(num, len(model_body.layers)))

    model_loss = Lambda(yolo_loss, output_shape=(1,), name='yolo_loss',
                        arguments={'anchors': anchors, 'num_classes': num_classes, 'ignore_thresh': 0.5})(
        [*model_body.output, *y_true])
    model = Model([model_body.input, *y_true], model_loss)

    return model


def _data_generator(annotation_lines, batch_size, input_shape, anchors, num_classes):
    n = len(annotation_lines)
    i = 0
    while True:
        image_data = []
        box_data = []
        for b in range(batch_size):
            if i == 0:
                np.random.shuffle(annotation_lines)
            image, box = get_random_data(annotation_lines[i], input_shape, random=True)
            image_data.append(image)
            box_data.append(box)
            i = (i + 1) % n
        image_data = np.array(image_data)
        box_data = np.array(box_data)
        y_true = preprocess_true_boxes(box_data, input_shape, anchors, num_classes)
        yield [image_data, *y_true], np.zeros(batch_size)


def data_generator(annotation_lines, batch_size, input_shape, anchors, num_classes):
    n = len(annotation_lines)
    if n == 0 or batch_size <= 0:
        return None
    return _data_generator(annotation_lines, batch_size, input_shape, anchors, num_classes)