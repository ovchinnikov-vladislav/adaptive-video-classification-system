import tensorflow as tf
import bmstu.capsnets.layers.basic as basic_layers
import bmstu.capsnets.layers.segment as segment_layers
import bmstu.layers as common_layers
import bmstu.capsnets.layers.gamma as gamma_layers
import bmstu.capsnets.layers.matrix as matrix_layers
import bmstu.capsnets.metrics.gamma as gamma_metrics
import bmstu.capsnets.metrics.matrix as matrix_metrics
from tensorflow.keras import activations, metrics
from bmstu.capsnets import losses
from bmstu.utls import pgd
from bmstu import utls


class MatrixCapsNet:
    def __init__(self, shape, classes, routings, batch_size, coord_add):
        self.inputs = tf.keras.layers.Input(shape=shape, batch_size=batch_size)
        self.conv1 = tf.keras.layers.Conv2D(filters=32, kernel_size=[5, 5], strides=2, padding='valid',
                                            activation=activations.relu)
        self.primaryCaps = matrix_layers.PrimaryCapsule2D(capsules=8, kernel_size=[1, 1], strides=1,
                                                          padding='valid', pose_shape=[4, 4])
        self.convCaps1 = matrix_layers.ConvolutionalCapsule(capsules=16, kernel=3, stride=2, routings=routings)
        self.convCaps2 = matrix_layers.ConvolutionalCapsule(capsules=16, kernel=3, stride=1, routings=routings)
        self.classCaps = matrix_layers.ClassCapsule(capsules=classes, routings=routings, coord_add=coord_add)

    def build(self):
        outputs = self.conv1(self.inputs)
        outputs = self.primaryCaps(outputs)
        outputs = self.convCaps1(outputs)
        outputs = self.convCaps2(outputs)
        outputs = self.classCaps(outputs)

        return MatrixCapsuleModel(self.inputs, outputs)


class GammaCapsNet(tf.keras.Model):
    # TODO: добить обучение Gamma СapsNet
    def __init__(self, shape, classes, routings, batch_size, gamma_robust=True):
        super(GammaCapsNet, self).__init__()
        self.gamma_robust = gamma_robust
        self.classes = classes
        self.batch_size = batch_size

        self.input_layer = tf.keras.layers.Reshape(target_shape=shape, input_shape=shape, batch_size=self.batch_size)
        self.conv1 = tf.keras.layers.Conv2D(256, (9, 9), padding='valid', activation=activations.relu)
        self.primaryCaps = basic_layers.PrimaryCapsule2D(capsules=32, dim_capsules=8, kernel_size=9, strides=2)
        self.gammaCaps1 = gamma_layers.GammaCapsule(capsules=32, dim_capsules=8, routings=routings)
        self.gammaCaps2 = gamma_layers.GammaCapsule(capsules=10, dim_capsules=16, routings=routings)
        self.decoder = gamma_layers.GammaDecoder(dim=28)
        self.norm = common_layers.Norm()

        self.input_decoder = tf.keras.layers.Input(shape=(classes,))
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        self.train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
        self.train_t_score = tf.keras.metrics.Mean(name='train_t_score')
        self.train_d_score = tf.keras.metrics.Mean(name='train_d_score')

        self.test_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='test_accuracy')
        self.test_loss = tf.keras.metrics.Mean(name='test_loss')
        self.test_t_score = tf.keras.metrics.Mean(name='test_t_score')
        self.test_d_score = tf.keras.metrics.Mean(name='test_d_score')

    def call(self, inputs, training=None, mask=None):
        x = self.input_layer(inputs)
        x = self.conv1(x)
        x = self.primaryCaps(x)
        v_1, c_1 = self.gammaCaps1(x)
        v_2, c_2 = self.gammaCaps2(v_1)

        r = self.decoder(v_2)
        out = self.norm(v_2)

        t_score = (gamma_metrics.t_score(c_1) + gamma_metrics.t_score(c_2)) / 2.0
        d_score = gamma_metrics.d_score(v_1)

        return out, r, [v_1, v_2], t_score, d_score

    def train_step(self, data):
        x, y = data
        x_adv = pgd(x, y, self, eps=0.1, a=0.01, k=40) if self.gamma_robust else x
        with tf.GradientTape() as tape:
            y_pred, reconstruction, _, t_score, d_score = self(x_adv, y)
            loss, _ = losses.compute_loss(y, y_pred, reconstruction, x)

        grads = tape.gradient(loss, self.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.trainable_variables))
        self.train_accuracy.update_state(y, y_pred)
        self.train_t_score.update_state(t_score)
        self.train_d_score.update_state(d_score)
        return {m.name: m.result() for m in self.metrics}

    def test_step(self, data):
        x, y = data
        y_pred, reconstruction, layers, t_score, d_score = self(x, y)
        loss, _ = losses.compute_loss(y, y_pred, reconstruction, x)

        self.test_accuracy.update_state(y, y_pred)
        self.test_loss.update_state(loss)
        self.test_t_score.update_state(t_score)
        self.test_d_score.update_state(d_score)

        pred = tf.argmax(y_pred, axis=1)
        cm = tf.math.confusion_matrix(y, pred, num_classes=self.classes)

        return {m.name: m.result() for m in self.metrics}

    def get_config(self):
        super(GammaCapsNet, self).get_config()


class MatrixCapsuleModel(tf.keras.Model):
    def train_step(self, data):
        x, y = data
        with tf.GradientTape() as tape:
            activation, pose = self(x, training=True)
            loss = losses.spread_loss(activation, pose, x, y, self.optimizer.learning_rate(self.optimizer.iterations))
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)

        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        self.compiled_metrics.update_state(y, activation)
        metrics = {m.name: m.result() for m in self.metrics}
        metrics['spread_loss'] = loss
        return metrics

    def test_step(self, data):
        x, y = data
        activation, pose = self(x, training=False)
        loss = losses.spread_loss(activation, pose, x, y, self.optimizer.learning_rate(self.optimizer.iterations))

        self.compiled_metrics.update_state(y, activation)

        metrics = {m.name: m.result() for m in self.metrics}
        metrics['spread_loss'] = loss
        return metrics


class SegCapsNetBasic:
    def __init__(self, shape, classes, routings):
        self.shape = shape
        self.classes = classes
        self.routings = routings

        self.input = tf.keras.layers.Input(shape=shape)
        self.conv1 = tf.keras.layers.Conv2D(filters=256, kernel_size=5, strides=1, padding='same',
                                            activation=activations.relu, name='conv1')
        self.primary_caps = segment_layers.ConvCapsuleLayer(kernel_size=5, num_capsule=8, num_atoms=32, strides=1,
                                                            padding='same', routings=1, name='primarycaps')
        self.seg_caps = segment_layers.ConvCapsuleLayer(kernel_size=1, num_capsule=1, num_atoms=16, strides=1,
                                                        padding='same', routings=routings, name='segcaps')
        self.out_seg = segment_layers.Length(num_classes=classes, seg=True, name='outseg')

    def build(self):
        conv1 = self.conv1(self.input)
        _, h, w, c = conv1.shape
        conv1_reshaped = tf.keras.layers.Reshape((h, w, 1, c))(conv1)
        primary_caps = self.primary_caps(conv1_reshaped)
        seg_caps = self.seg_caps(primary_caps)
        out_seg = self.out_seg(seg_caps)

        _, h, w, c, a = seg_caps.shape
        y = tf.keras.layers.Input(shape=list(self.shape[:-1])+list((1,)))
        masked_by_y = segment_layers.Mask()([seg_caps, y])
        masked = segment_layers.Mask()(seg_caps)

        def shared_decoder(mask_layer):
            recon_remove_dim = tf.keras.layers.Reshape((h, w, a))(mask_layer)
            recon_1 = tf.keras.layers.Conv2D(filters=64, kernel_size=1, padding='same',
                                             kernel_regularizer=tf.keras.initializers.get('he_normal'),
                                             activation=activations.relu, name='recon_1')(recon_remove_dim)
            recon_2 = tf.keras.layers.Conv2D(filters=128, kernel_size=1, padding='same',
                                             kernel_regularizer=tf.keras.initializers.get('he_normal'),
                                             activation=activations.relu, name='recon_2')(recon_1)
            out_recon = tf.keras.layers.Conv2D(filters=1, kernel_size=1, padding='same',
                                               kernel_regularizer=tf.keras.initializers.get('he_normal'),
                                               activation=activations.sigmoid, name='out_recon')(recon_2)

            return out_recon

        train_model = tf.keras.Model([self.input, y], [out_seg, shared_decoder(masked_by_y)])
        eval_model = tf.keras.Model(self.input, [out_seg, shared_decoder(masked)])

        noise = tf.keras.layers.Input((h, w, c, a))
        noised_seg_caps = tf.keras.layers.Add()([seg_caps, noise])
        masked_noised_y = segment_layers.Mask()([noised_seg_caps, y])
        manipulate_model = tf.keras.Model([self.input, y, noise], shared_decoder(masked_noised_y))

        return train_model, eval_model, manipulate_model


class DarkNet():
    def build(self):
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.Conv2D(32, 3, strides=(1, 1), padding=1))
        model.add(tf.keras.layers.BatchNormalization(momentum=0.01))


# if __name__ == '__main__':
#     (x_train, y_train), (x_test, y_test) = utls.load('mnist')
#
#     model = GammaCapsNet(shape=[28, 28, 1], num_classes=10, routings=3, batch_size=64)
#     model.build((64, 28, 28, 1))
#     model.summary()
#     model.compile()
#     model.fit(x_train, y_train, batch_size=64, epochs=5,
#               validation_data=[x_test, y_test])

# if __name__ == '__main__':
#     import numpy as np
#
#     coord_add = [[[8., 8.], [12., 8.], [16., 8.]],
#                  [[8., 12.], [12., 12.], [16., 12.]],
#                  [[8., 16.], [12., 16.], [16., 16.]]]
#
#     coord_add = np.array(coord_add, dtype=np.float32) / 28.
#
#     (x_train, y_train), (x_test, y_test) = utls.load('fashion_mnist')
#     x_val = x_test[:9000]
#     y_val = y_test[:9000]
#     x_test = x_test[9000:]
#     y_test = y_test[9000:]
#
#     epochs = 2
#     batch_size = 25
#
#     model = MatrixCapsNet([28, 28, 1], 10, 3, batch_size, coord_add).build()
#     model.summary()
#
#     model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=tf.keras.optimizers.schedules.PiecewiseConstantDecay(
#         boundaries=[(len(x_train) // batch_size * x) for x in
#                     range(1, 8)],
#         values=[x / 10.0 for x in range(2, 10)])),
#         metrics=matrix_metrics.matrix_accuracy)
#
#     model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs,
#               validation_data=(x_val, y_val))
#
#     print(y_test[0])
#     activation, pose_out = model.predict(x_test[0])
#     print(activation)

if __name__ == '__main__':
    segmodel = SegCapsNetBasic([28, 28, 1], 10, 3).build()
    segmodel[0].summary()