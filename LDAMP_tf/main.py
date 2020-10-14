#TODO tensorflow version 2.X migration code changed the import tensorflow as tf line to two lines as seen below
# import tensorflow.compat.v1 as tf
# tf.disable_eager_execution()
import tensorflow as tf
import numpy as np
import reconstruction_methods as rms
import utils
import sensing_methods as sms
import os
os.environ["CUDA_VISIBLE_DEVICES"]='1'

# from tensorflow.python.client import device_lib
# print(device_lib.list_local_devices())

def main(sensing,reconstruction,stage,default,dataset,input_channel,input_width,input_height,m,n,specifics):
    if default==True:
        sensing = sensing
        reconstruction = reconstruction
        stage = stage
        dataset = dataset

        input_channel = input_channel
        input_width = input_width
        input_height = input_height

        # needed to calculate matrices sizes
        sampling_rate = .2
        sigma_w = 1. / 255.  # Noise std

        n = input_channel * input_height * input_width
        m = int(np.round(sampling_rate * n))
        specifics = {
            'channel_img': 1,
            'width_img': input_width,
            'height_img': input_height,
            'sampling_rate': sampling_rate,
            'n': 1 * input_height * input_width,
            'm': int(np.round(sampling_rate * 1 * input_height * input_width)),
            'alg': 'DAMP',
            'tie_weights': False,  # if true set LayerByLayer to False
            'filter_height': 3,
            'filter_width': 3,
            'num_filters': 64,
            'n_DnCNN_layers': 16,
            'max_n_DAMP_layers': 10,
            # Unless FLAGS.start_layer is set to this value or LayerbyLayer=false, the code will sequentially train larger and larger networks end-to-end.

            ## Training Parameters
            'start_layer': 1,
            'max_Epoch_Fails': 3,  # How many training epochs to run without improvement in the validation error
            'ResumeTraining': False,  # Load weights from a network you've already trained a little
            'LayerbyLayer': True,  # Train only the last layer of the network
            'DenoiserbyDenoiser': True,  # if this is true, overrides other two
            'sigma_w_min': 25,
            'sigma_w_max': 25,
            'sigma_w': 25. / 255.,  # Noise std
            'learning_rates': [0.001, 0.0001],  # , 0.00001]
            'EPOCHS': 50,
            'n_Train_Images': 128 * 1600,  # 128*3000
            'n_Val_Images': 10000,  # 10000
            'BATCH_SIZE': 128, # 128 for training, 1 for testing
            'InitWeightsMethod': 'smaller net', #Options are random, denoiser, smaller net, and layer_by_layer.
            'loss_func': 'MSE',
            'init_mu': 0,
            'init_sigma': 0.1,
            'mode': 'gaussian',
            'validation_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/ValidationData_patch',
            'training_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/TrainingData_patch',
            'testing_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/StandardTestData_256Res.npy'
        }

    dset=utils.generate_dataset(dataset,input_channel,input_width,input_height,stage) # unused, just used to pass in
    sensing_method=sms.sensing_method(reconstruction,specifics) # unused, just used to pass in
    reconstruction_method=rms.reconstruction_method(dset, reconstruction,specifics)
    # put result of the parameters into specifics.
    reconstruction_method.initialize(dset,sensing_method, stage)
    reconstruction_method.run()

if __name__ == "__main__":

    input_width = 40
    input_height = 40
    sampling_rate = .2
    main(
        'gaussian', # sensing type
        "DAMP", #put DAMP instead of LDAMP
        "training", # stage
        False, # default, switch to false if want to edit parameters below
        '', # dataset is not used
        1, # input channels
        input_width, # input width
        input_height, # input height
        int(np.round(sampling_rate * 1 * input_height * input_width)),  # m 320
        input_width * input_height * 1, # n 40x40x1
        {
            'channel_img': 1,
            'width_img': input_width,
            'height_img': input_height,
            'sampling_rate': sampling_rate,
            'n': 1 * input_height * input_width,
            'm': int(np.round(sampling_rate * 1 * input_height * input_width)),
            'alg': 'DAMP',
            'tie_weights': False,  # if true set LayerByLayer to False
            'filter_height': 3,
            'filter_width': 3,
            'num_filters': 64,
            'n_DnCNN_layers': 16,
            'max_n_DAMP_layers': 10,
            # Unless FLAGS.start_layer is set to this value or LayerbyLayer=false, the code will sequentially train larger and larger networks end-to-end.

            ## Training Parameters
            'start_layer': 1,
            'max_Epoch_Fails': 3,  # How many training epochs to run without improvement in the validation error
            'ResumeTraining': False,  # Load weights from a network you've already trained a little
            'LayerbyLayer': True,  # Train only the last layer of the network
            'DenoiserbyDenoiser': False,  # if this is true, overrides other two
            'sigma_w_min': 25, # only used in denoiserbydenoiser training
            'sigma_w_max': 25, # only used in denoiserbydenoiser training
            'sigma_w': 1./255.,  # Noise std (LbL testing: 0, LbL training: 1./255., DbD test and train: 25./255.)
            'learning_rates': [0.001, 0.0001],  # , 0.00001]
            'EPOCHS': 50,
            'n_Train_Images': 128 * 1600,  # 128*3000
            'n_Val_Images': 10000,  # 10000
            'BATCH_SIZE': 128, # 128 for training, 1 for testing
            'InitWeightsMethod': 'smaller net', #Options are random, denoiser, smaller net, and layer_by_layer.
            'loss_func': 'MSE',
            'init_mu': 0,
            'init_sigma': 0.1,
            'mode': 'gaussian',
            'validation_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/ValidationData_patch',
            'training_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/TrainingData_patch',
            'testing_patch': '/home/user/mkweste1/LDAMP_final_tf/Data/StandardTestData_256Res.npy'
        },
    )