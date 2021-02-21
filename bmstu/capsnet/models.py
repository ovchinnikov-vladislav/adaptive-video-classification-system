import tensorflow as tf
import bmstu.capsnet.layers.basic as basic_layers
import bmstu.layers as common_layers
import bmstu.capsnet.layers.gamma as gamma_layers


class CapsNet:
    def __init__(self, shape, classes, routings):
        self.shape = shape
        self.classes = classes

        self.input_capsnet = tf.keras.layers.Input(shape=shape)
        self.conv1 = tf.keras.layers.Conv2D(256, (9, 9), padding='valid', activation=tf.nn.relu)
        self.primaryCaps = basic_layers.PrimaryCapsule(capsules=32, dim_capsules=8, kernel_size=9, strides=2)
        self.capsules = basic_layers.Capsule(capsules=classes, dim_capsules=16, routings=routings)
        self.output = basic_layers.Length()

        self.input_decoder = tf.keras.layers.Input(shape=(classes,))
        self.input_noise_decoder = tf.keras.layers.Input(shape=(classes, 16))

    def build(self):
        self.conv1 = self.conv1(self.input_capsnet)
        self.primaryCaps = self.primaryCaps(self.conv1)
        self.capsules = self.capsules(self.primaryCaps)
        self.output = self.output(self.capsules)

        train_model = tf.keras.models.Model(
            [self.input_capsnet, self.input_decoder],
            [self.output, basic_layers.Decoder(
                classes=self.classes, output_shape=self.shape)([self.capsules, self.input_decoder])])

        eval_model = tf.keras.models.Model(
            self.input_capsnet,
            [self.output, basic_layers.Decoder(classes=self.classes, output_shape=self.shape)(self.capsules)])

        noised_digitcaps = tf.keras.layers.Add()([self.capsules, self.input_noise_decoder])
        manipulate_model = tf.keras.models.Model(
            [self.input_capsnet, self.input_decoder, self.input_noise_decoder],
            basic_layers.Decoder(classes=self.classes, output_shape=self.shape)([noised_digitcaps, self.input_decoder]))

        return train_model, eval_model, manipulate_model


class GammaCapsNet:

    def __init__(self, shape, classes, routings):
        super(GammaCapsNet, self).__init__()
        self.input_capsnet = tf.keras.layers.Input(shape=shape)
        self.conv1 = tf.keras.layers.Conv2D(256, (9, 9), padding='valid', activation=tf.nn.relu)
        self.primaryCaps = basic_layers.PrimaryCapsule(capsules=32, dim_capsules=8, kernel_size=9, strides=2)
        self.gammaCaps1 = gamma_layers.GammaCapsule(capsules=32, dim_capsules=8, routings=routings)
        self.gammaCaps2 = gamma_layers.GammaCapsule(capsules=10, dim_capsules=16, routings=routings)
        self.decoder = gamma_layers.GammaDecoder(dim=28)
        self.norm = common_layers.Norm()

        self.input_decoder = tf.keras.layers.Input(shape=(classes,))

        self.model = None

    def build(self):
        x = self.conv1(self.input_capsnet)
        x = self.primaryCaps(x)
        v_1, c_1 = self.gammaCaps1(x)
        v_2, c_2 = self.gammaCaps2(v_1)

        r = self.decoder(v_2)
        out = self.norm(v_2)

        self.model = tf.keras.models.Model(self.input_capsnet, [out, r])
        return self.model

    def fit(self, train_data, validation_data):
        assert self.model is None, 'GammaCapsNet model should be building'
        # TODO: дописать кастомное обучение модели
        pass
