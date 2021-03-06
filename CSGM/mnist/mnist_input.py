"""Inputs for MNIST dataset"""

import math
import numpy as np
import glob
import dcgan.dcgan_utils as dcgan_utils
import mnist.mnist_model_def as mnist_model_def
import tensorflow.compat.v1 as tf
from tensorflow.examples.tutorials.mnist import input_data

NUM_TEST_IMAGES = 10000


def get_random_test_subset(mnist, sample_size):
    """Get a small random subset of test images"""
    idxs = np.random.choice(NUM_TEST_IMAGES, sample_size)
    images = [mnist.test.images[idx] for idx in idxs]
    images = {i: image for (i, image) in enumerate(images)}
    
    return images


def sample_generator_images(hparams):
    """Sample random images from the generator"""

    # Create the generator
    _, x_hat, restore_path, restore_dict = mnist_model_def.vae_gen(hparams)

    # Get a session
    sess = tf.Session()

    # Intialize and restore model parameters
    init_op = tf.global_variables_initializer()
    sess.run(init_op)

    restorer = tf.train.Saver(var_list=restore_dict)
    restorer.restore(sess, restore_path)

    images = {}
    counter = 0
    rounds = int(math.ceil(hparams.num_input_images/hparams.batch_size))
    for _ in range(rounds):
        images_mat = sess.run(x_hat)
        for (_, image) in enumerate(images_mat):
            if counter < hparams.num_input_images:
                images[counter] = image
                counter += 1

    # Reset TensorFlow graph
    sess.close()
    tf.reset_default_graph()

    return images


def model_input(hparams):
    """Create input tensors"""

    mnist = input_data.read_data_sets('./data/mnist', one_hot=True)

    if hparams.input_type == 'full-input':
        image_paths = glob.glob(hparams.input_path_pattern)
        image_paths= image_paths[:hparams.num_input_images]
        image_paths.sort() 

        images = [dcgan_utils.get_image(image_path,hparams.input_size,True,hparams.input_size,True) for image_path in image_paths]#images = [dcgan_utils.get_image(image_path, image_size) for image_path in image_paths]
        images = {i: image.reshape([hparams.input_size*hparams.input_size*1])/2+0.5 for (i, image) in enumerate(images)}

    elif hparams.input_type == 'random-test':
        images = get_random_test_subset(mnist, hparams.num_input_images)
    elif hparams.input_type == 'gen-span':
        images = sample_generator_images(hparams)
    else:
        raise NotImplementedError

    return images
