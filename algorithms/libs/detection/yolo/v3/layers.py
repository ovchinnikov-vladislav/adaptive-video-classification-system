import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import (Concatenate, Input, Lambda, UpSampling2D)
from libs.detection.darknet53.layers import darknet_conv, darknet53, darknet53_tiny


def yolo_conv_input_tuple(x_in, filters):
    inputs = Input(x_in[0].shape[1:]), Input(x_in[1].shape[1:])
    x, x_skip = inputs

    # concat with skip connection
    x = darknet_conv(x, filters, 1)
    x = UpSampling2D(2)(x)
    x = Concatenate()([x, x_skip])

    return x, inputs


def yolo_conv(x_in, filters, name=None):
    if isinstance(x_in, tuple):
        x, inputs = yolo_conv_input_tuple(x_in, filters)
    else:
        x = inputs = Input(x_in.shape[1:])

    x = darknet_conv(x, filters, 1)
    x = darknet_conv(x, filters * 2, 3)
    x = darknet_conv(x, filters, 1)
    x = darknet_conv(x, filters * 2, 3)
    x = darknet_conv(x, filters, 1)
    return Model(inputs, x, name=name)(x_in)


def yolo_conv_tiny(x_in, filters, name=None):
    if isinstance(x_in, tuple):
        x, inputs = yolo_conv_input_tuple(x_in, filters)
    else:
        x = inputs = Input(x_in.shape[1:])
        x = darknet_conv(x, filters, 1)

    return Model(inputs, x, name=name)(x_in)


def yolo_output(x_in, filters, anchors, classes, name=None):
    x = inputs = Input(x_in.shape[1:])
    x = darknet_conv(x, filters * 2, 3)
    x = darknet_conv(x, anchors * (classes + 5), 1, batch_norm=False)
    x = Lambda(lambda inp: tf.reshape(inp, (-1, inp.shape[1], inp.shape[2], anchors, classes + 5)))(x)
    return tf.keras.Model(inputs, x, name=name)(x_in)


def yolo_v3(anchors, size, channels, classes, training=False, yolo_max_boxes=30):
    masks = np.array([[6, 7, 8], [3, 4, 5], [0, 1, 2]])

    x = inputs = Input([size, size, channels], name='input')
    darknet = darknet53(name='yolo_darknet', size=size, channels=channels)

    x_36, x_61, x = darknet(x)

    x = yolo_conv(x, 512, name='yolo_conv_0')
    output_0 = yolo_output(x, 512, len(masks[0]), classes, name='yolo_output_0')

    x = yolo_conv((x, x_61), 256, name='yolo_conv_1')
    output_1 = yolo_output(x, 256, len(masks[1]), classes, name='yolo_output_1')

    x = yolo_conv((x, x_36), 128, name='yolo_conv_2')
    output_2 = yolo_output(x, 128, len(masks[2]), classes, name='yolo_output_2')

    if training:
        return Model(inputs, (output_0, output_1, output_2), name='yolo3')

    from libs.detection.utils import yolo_boxes, yolo_nms
    boxes_0 = Lambda(lambda inp: yolo_boxes(inp, anchors[masks[0]], classes), name='yolo_boxes_0')(output_0)
    boxes_1 = Lambda(lambda inp: yolo_boxes(inp, anchors[masks[1]], classes), name='yolo_boxes_1')(output_1)
    boxes_2 = Lambda(lambda inp: yolo_boxes(inp, anchors[masks[2]], classes), name='yolo_boxes_2')(output_2)

    outputs = Lambda(lambda inp: yolo_nms(inp, num_classes=classes, yolo_max_boxes=yolo_max_boxes), name='yolo_nms')((boxes_0[:3], boxes_1[:3], boxes_2[:3]))

    return Model(inputs, outputs, name='yolo3')


def yolo_v3_tiny(anchors, size, channels, classes, training=False):
    masks = np.array([[3, 4, 5], [0, 1, 2]])

    x = inputs = Input([size, size, channels], name='input')

    x_8, x = darknet53_tiny(name='yolo_darknet', channels=channels)(x)

    x = yolo_conv_tiny(x, 256, name='yolo_conv_0')
    output_0 = yolo_output(x, 256, len(masks[0]), classes, name='yolo_output_0')

    x = yolo_conv_tiny((x, x_8), 128, name='yolo_conv_1')
    output_1 = yolo_output(x, 128, len(masks[1]), classes, name='yolo_output_1')

    if training:
        return Model(inputs, (output_0, output_1), name='yolo3')

    from libs.detection.utils import yolo_boxes, yolo_nms
    boxes_0 = Lambda(lambda inp: yolo_boxes(inp, anchors[masks[0]], classes), name='yolo_boxes_0')(output_0)
    boxes_1 = Lambda(lambda inp: yolo_boxes(inp, anchors[masks[1]], classes), name='yolo_boxes_1')(output_1)
    outputs = Lambda(lambda inp: yolo_nms(inp, num_classes=classes), name='yolo_nms')((boxes_0[:3], boxes_1[:3]))
    return Model(inputs, outputs, name='yolo3_tiny')


if __name__ == '__main__':
    from libs.detection.utils import get_anchors
    import config
    anchors = get_anchors(config.yolo_v3_anchors)

    model = yolo_v3(anchors, 416, 3, 2, False)
    from libs.detection.utils import freeze_to

    freeze_to(model.get_layer('yolo_darknet'), 75)
    # model.summary(line_length=250)