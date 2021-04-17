import io
import itertools
import math
import os
import datetime
from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
import numpy as np
import pandas
import tensorflow as tf
import uuid
from tensorflow.keras import callbacks
from tensorflow.keras.datasets import mnist, fashion_mnist, cifar10, cifar100
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.utils import to_categorical, plot_model


def pgd(x, y, model, eps=0.3, k=40, a=0.01):
    """ Projected gradient descent (PGD) attack
    """
    x_adv = tf.identity(x)
    loss_fn = tf.nn.softmax_cross_entropy_with_logits

    for _ in range(k):
        with tf.GradientTape(watch_accessed_variables=False) as tape:
            tape.watch(x_adv)
            y_pred, _, _, _, _ = model(x_adv, y)
            classes = tf.shape(y_pred)[1]
            labels = tf.one_hot(y, classes)
            loss = loss_fn(labels=labels, logits=y_pred)
        dl_dx = tape.gradient(loss, x_adv)
        x_adv += a * tf.sign(dl_dx)
        x_adv = tf.clip_by_value(x_adv, x - eps, x + eps)
        x_adv = tf.clip_by_value(x_adv, 0.0, 1.0)

    print('Finished attack', flush=True)
    return x_adv


def combine_images(generated_images, height=None, width=None):
    num = generated_images.shape[0]
    if width is None and height is None:
        width = int(math.sqrt(num))
        height = int(math.ceil(float(num) / width))
    elif width is not None and height is None:  # height not given
        height = int(math.ceil(float(num) / width))
    elif height is not None and width is None:  # width not given
        width = int(math.ceil(float(num) / height))

    shape = generated_images.shape[1:3]
    image = np.zeros((height * shape[0], width * shape[1]),
                     dtype=generated_images.dtype)
    for index, img in enumerate(generated_images):
        i = int(index / width)
        j = index % width
        image[i * shape[0]:(i + 1) * shape[0], j * shape[1]:(j + 1) * shape[1]] = \
            img[:, :, 0]
    return image


def plot_log(filename, show=True):
    data = pandas.read_csv(filename)

    fig = plt.figure(figsize=(4, 6))
    fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95)
    fig.add_subplot(211)
    for key in data.keys():
        if key.find('loss') >= 0 and not key.find('val') >= 0:  # training loss
            plt.plot(data['epoch'].values, data[key].values, label=key)
    plt.legend()
    plt.title('Потери (loss) при тренировке')

    fig.add_subplot(212)
    for key in data.keys():
        if key.find('acc') >= 0:  # acc
            plt.plot(data['epoch'].values, data[key].values, label=key)
    plt.legend()
    plt.title('Точность (accuracy) при тренировке и валидации')

    fig.savefig('log.png')
    if show:
        plt.show()


def plot_to_image(figure):
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(figure)
    buf.seek(0)
    image = tf.image.decode_png(buf.getvalue(), channels=4)
    image = tf.expand_dims(image, 0)
    return image


def plot_confusion_matrix(cm, class_names):
    figure = plt.figure(figsize=(8, 8))
    plt.imshow(cm, interpolation='nearest', cmap=plt.get_cmap('Blues'))
    plt.title('Матрица ошибок')
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)

    cm = np.around(cm.astype('float') / cm.sum(axis=1)[:, np.newaxis], decimals=4)

    threshold = cm.max(initial=0) / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        color = 'white' if cm[i, j] > threshold else 'black'
        plt.text(j, i, cm[i, j], horizontalalignment="center", color=color)

    plt.tight_layout()
    plt.ylabel('Входные метки')
    plt.xlabel('Предсказанные метки')
    return figure


def plot_classification_report(cr, title='Отчет по классификации', with_avg_total=False, cmap=plt.get_cmap('Blues')):
    lines = cr.split('\n')
    classes = []
    plot_mat = []
    t = None
    for line in lines[2: (len(lines) - 3)]:
        t = line.split()
        classes.append(t[0])
        v = [float(x) for x in t[1: len(t) - 1]]
        plot_mat.append(v)

    if with_avg_total:
        ave_total = lines[len(lines) - 1].split()
        classes.append('avg/total')
        v_ave_total = [float(x) for x in t[1:len(ave_total) - 1]]
        plot_mat.append(v_ave_total)

    plt.imshow(plot_mat, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    x_tick_marks = np.arange(3)
    y_tick_marks = np.arange(len(classes))
    plt.xticks(x_tick_marks, ['точность (precision)', 'полнота (recall)', 'f1-score'], rotation=45)
    plt.yticks(y_tick_marks, classes)
    plt.tight_layout()
    plt.ylabel('Классы')
    plt.xlabel('Метрики')


def plot_generated_image(x, y_pred):
    classes = tf.shape(y_pred)
    y_pred = y_pred.numpy()

    figure = plt.figure()
    plt.imshow(x, cmap=plt.get_cmap('gray'))
    text = ""
    for i in range(classes):
        text += "%d: %.2f " % (i, y_pred[i])
        if (i + 1) % 5 == 0 and i > 0:
            text += "\n"

    plt.title(text)
    return figure


def load(dataset):
    if dataset == 'mnist':
        shape = [-1, 28, 28, 1]
        (x_train, y_train), (x_test, y_test) = mnist.load_data()
    elif dataset == 'fashion_mnist':
        shape = [-1, 28, 28, 1]
        (x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()
    elif dataset == 'cifar10':
        shape = [-1, 32, 32, 3]
        (x_train, y_train), (x_test, y_test) = cifar10.load_data()
    elif dataset == 'cifar100':
        shape = [-1, 32, 32, 3]
        (x_train, y_train), (x_test, y_test) = cifar100.load_data()
    else:
        raise Exception('undefined name dataset')

    x_train = x_train.reshape(shape).astype('float32') / 255.
    x_test = x_test.reshape(shape).astype('float32') / 255.
    y_train = to_categorical(y_train.astype('float32'))
    y_test = to_categorical(y_test.astype('float32'))

    return (x_train, y_train), (x_test, y_test)


class BaseModelForTraining(ABC):
    def __init__(self, name):
        self.models = None
        self.training_model = None
        self.input_shape = None
        self.is_decoder = None
        self.batch_size = None
        self.name = name

    @abstractmethod
    def create(self, input_shape, **kwargs):
        pass

    def build(self, input_shape, **kwargs):
        self.input_shape = input_shape

        self.models = self.create(input_shape, **kwargs)

        if type(self.models) is tuple:
            self.training_model = self.models[0]
        else:
            self.training_model = self.models

        self.training_model.summary()

        return self.models

    def compile(self, **kwargs):
        self.training_model.compile(**kwargs)

    def __train_generator(self, x, y, shift_fraction=0.):
        train_data_generator = ImageDataGenerator(width_shift_range=shift_fraction,
                                                  height_shift_range=shift_fraction)
        generator = train_data_generator.flow(x, y, batch_size=self.batch_size)
        while 1:
            x_batch, y_batch = generator.next()
            if self.is_decoder:
                yield [x_batch, y_batch], [y_batch, x_batch]
            else:
                yield x_batch, y_batch

    def __test_generator(self, x, y):
        if self.is_decoder:
            return [x, y], [y, x]
        else:
            return x, y

    def fit(self, x, y, batch_size, epochs, call_backs=None, load_weights=None, validation_data=None,
            set_plot_model=True, set_tensor_board=True, set_debug=False, set_model_checkpoint=True,
            set_csv_logger=True, log_dir='./', show_plot_logs=False, save_weights=True, checkpoint_monitor='accuracy'):
        if call_backs is None:
            call_backs = []
        cb = []
        cb += call_backs
        self.batch_size = batch_size

        if not os.path.exists(os.path.join(log_dir, 'models')):
            os.makedirs(os.path.join(log_dir, 'models'))

        if set_csv_logger:
            cb.append(callbacks.CSVLogger(os.path.join(log_dir, 'history.csv')))

        if set_tensor_board:
            cb.append(callbacks.TensorBoard(log_dir=os.path.join(log_dir, 'tb'),
                                            batch_size=self.batch_size, histogram_freq=set_debug))
        if set_model_checkpoint:
            date = str(datetime.datetime.now()).split(' ')[0]
            file_name = f'{self.name}-{date}' + '-{epoch:02d}.h5'
            cb.append(callbacks.ModelCheckpoint(
                os.path.join(log_dir, 'models', file_name), monitor=checkpoint_monitor,
                save_best_only=True, save_weights_only=True, verbose=1))

        if set_plot_model:
            plot_model(self.training_model, to_file=os.path.join(log_dir, self.name + '.svg'), show_shapes=True)

        if load_weights:
            self.training_model.load_weights(load_weights)

        history = self.training_model.fit(self.__train_generator(x, y, 0.1), epochs=epochs,
                                          validation_data=self.__test_generator(validation_data[0], validation_data[1]),
                                          steps_per_epoch=int(y.shape[0] / batch_size), callbacks=cb)

        if save_weights:
            date = str(datetime.datetime.now()).split(' ')[0]
            self.training_model.save(os.path.join(log_dir, f'{self.name}-result-{date}-{str(uuid.uuid4())}.h5'))

        if show_plot_logs:
            plot_log(os.path.join(log_dir, 'history.csv'), True)

        return history
