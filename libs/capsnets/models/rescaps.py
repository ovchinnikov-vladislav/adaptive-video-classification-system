from libs.capsnets.layers.basic import Decoder
from libs.capsnets.layers.residual import PrimaryCapsule2D, Capsule, res_block_caps, Length
from tensorflow.keras.layers import (Input, Conv2D, Add, BatchNormalization, LeakyReLU,
                                     Reshape, Concatenate, Activation, Dropout)
from tensorflow.keras.models import Model
import tensorflow as tf
from libs import utls
from libs.resnets.blocks import relu_bn, residual_block, identity_block, conv_block


class ResCapsuleNetworkV1(utls.BaseModelForTraining):
    def create(self, input_shape, **kwargs):
        self.is_decoder = True

        num_classes = kwargs.get('num_classes')
        routings = kwargs.get('routings')

        x = inputs = Input(shape=input_shape)
        num_filters = 64

        t = BatchNormalization()(x)
        t = Conv2D(kernel_size=3,
                   strides=1,
                   filters=num_filters,
                   padding="same")(t)
        t = relu_bn(t)

        num_blocks_list = [2, 5, 5, 2]
        for i in range(len(num_blocks_list)):
            num_blocks = num_blocks_list[i]
            for j in range(num_blocks):
                t = residual_block(t, downsample=(j == 0 and i != 0), filters=num_filters)
            num_filters *= 2

        _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=4, strides=1)(t)
        capsules = Capsule(num_capsules=num_classes, dim_capsules=16, routings=routings)(capsules)
        output = Length()(capsules)

        input_decoder = Input(shape=(num_classes,))

        train_model = Model([inputs, input_decoder],
                            [output, Decoder(num_classes=num_classes, output_shape=input_shape)([capsules, input_decoder])])

        eval_model = Model(inputs, [output, Decoder(num_classes=num_classes, output_shape=input_shape)(capsules)])

        return train_model, eval_model


def residual_primary_caps_block(x, kernel_size=5, downsample=False):
    _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=kernel_size, strides=1)(x)
    _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=kernel_size, strides=1)(x)

    if downsample:
        _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=kernel_size, strides=1)(x)
    out = Add()([x, capsules])
    return out


def res_primary_caps(shape, num_classes, routings):
    input_capsnet = Input(shape=shape)

    capsules = Conv2D(256, (9, 9), padding='valid', activation=tf.nn.relu)(input_capsnet)
    _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=9, strides=2)(capsules)
    # x = residual_primary_caps_block(capsules)
    # x = residual_primary_caps_block(x)
    # x = residual_primary_caps_block(x)
    # x = residual_primary_caps_block(x)
    # x = residual_primary_caps_block(x)

    capsules = Capsule(num_capsules=num_classes, dim_capsules=16, routings=routings)(capsules)
    output = Length()(capsules)

    train_model = Model(input_capsnet, output)

    return train_model


def res_capsnet(shape, num_classes, routings):
    x = inputs = Input(shape=shape)

    x = Conv2D(256, (9, 9), padding='valid', activation=tf.nn.relu)(x)
    capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=9, strides=2)(x)
    capsules = Capsule(num_capsules=num_classes, dim_capsules=16, routings=routings)(capsules)
    output = Length(name='length')(capsules)

    input_decoder = Input(shape=(num_classes,))

    decoder = Decoder(name='is_decoder', num_classes=num_classes, dim=18, output_shape=shape)

    train_model = Model([inputs, input_decoder],
                        [output, decoder([capsules, input_decoder])])

    eval_model = Model(inputs, [output, decoder(capsules)])

    return train_model, eval_model


def res50_caps(shape, num_classes, routings):
    input = Input(shape=shape)

    x = Conv2D(64, (7, 7), strides=(2, 2), name='conv1')(input)
    x = BatchNormalization(axis=-1, name='bn_conv1')(x)
    x = Activation('relu')(x)

    x = conv_block(x, 3, [64, 64, 256], stage=2, block='a', strides=(1, 1))
    x = identity_block(x, 3, [64, 64, 256], stage=2, block='b')
    x = identity_block(x, 3, [64, 64, 256], stage=2, block='c')

    x = conv_block(x, 3, [128, 128, 512], stage=3, block='a')
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='b')
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='c')
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='d')

    x = conv_block(x, 3, [256, 256, 1024], stage=4, block='a')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='b')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='c')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='d')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='e')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='f')

    x = conv_block(x, 3, [512, 512, 2048], stage=5, block='a')
    x = identity_block(x, 3, [512, 512, 2048], stage=5, block='b')
    x = identity_block(x, 3, [512, 512, 2048], stage=5, block='c')

    _, capsules = PrimaryCapsule2D(num_capsules=32, dim_capsules=8, kernel_size=2, strides=2)(x)
    capsules = Capsule(num_capsules=num_classes, dim_capsules=16, routings=routings)(capsules)
    output = Length()(capsules)

    train_model = Model(input, output)

    return train_model

