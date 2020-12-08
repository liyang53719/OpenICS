import reconstruction_methods as rms
import utils
import json

def main(sensing,reconstruction,stage,default,dataset,input_channel,input_width,input_height,m,n,specifics):
    if default==True:
        dataset = 'Training_Data.mat'
        input_channel = 1 # restricted to 1
        input_width = 33 # restricted to 33
        input_height = 33 # restricted to 33
        m = 1089
        n = 272 # ratio_dict = {1: 10, 4: 43, 10: 109, 25: 272, 30: 327, 40: 436, 50: 545}
        # specifics = {
        #     'stage': stage,
        #     'start_epoch': 0,
        #     'end_epoch': 200,
        #     'testing_epoch_num': 60,
        #     'learning_rate': 1e-4,
        #     'layer_num': 9,
        #     'group_num': 2, # check to make sure group matches folder
        #     'cs_ratio': 25,
        #     'input_width': input_width,
        #     'n': n,
        #     'm': m,
        #     'nrtrain': 88912,
        #     'batch_size': 64,
        #
        #     'model_dir': 'model',
        #     'log_dir': 'log',
        #     'data_dir': 'data',
        #     'result_dir': 'result',
        #     'matrix_dir': 'sampling_matrix',
        #
        #     'use_universal_matrix': False, # unused in original
        #     'create_custom_dataset': False, # unused in original
        #     'custom_dataset_name': "", # unused in original
        #     'custom_training_data_location': '', # unused in original
        #     'custom_type_of_image': '', # unused in original
        #
        #     'training_data_fileName': 'Training_Data',
        #     'training_data_type': 'mat',
        #     'Testing_data_location': 'Set11',
        #     'testing_data_isFolderImages': True,
        #     'testing_data_type': 'tif',
        # }

        with open('./original_specifics.json', 'r') as fp:
            specifics = json.load(fp)


    dset = utils.generate_dataset(input_channel,input_width,input_height, stage, specifics)
    # sensing_method=sms.sensing_method(sensing, specifics) # not used
    reconstruction_method=rms.reconstruction_method(reconstruction,specifics)
    reconstruction_method.initialize(dset, specifics)
    reconstruction_method.run()
        
if __name__ == "__main__":
    input_width = 28
    ratio = 25
    stage = 'testing'

    m = input_width*input_width
    n = int(ratio/100 * m)
    main(
        "random",
        "ISTANetPlus", # "ISTANet", "ISTANetPlus"
        stage,
        False, # use paper's original parameters/data
        0, # dataset unused
        1, # channel
        input_width,
        input_width,
        m,
        n,
        specifics={
            'stage': stage,
            'start_epoch': 0,
            'end_epoch': 50,
            'testing_epoch_num': 5,
            'learning_rate': 1e-4,
            'layer_num': 9,
            'group_num': 69, # organizational purposes
            'cs_ratio': ratio,
            'input_width': input_width,
            'n': n,
            'm': m,
            'nrtrain': 60000, #224000, #88912, 867, 224000
            'batch_size': 64, # 64 for train

            # customize your directory names
            'model_dir': 'model',
            'log_dir': 'log',
            'data_dir': 'data',
            'result_dir': 'result',
            'matrix_dir': 'sampling_matrix',

            # Typically keep True
            # (set to False to use original paper's preloaded matrices which only supports imgs 33x33)
            'use_universal_matrix': True,

            # (Training only) set to True and define custom name, location, and type.
            # Will then create and train on this new dataset
            'create_custom_dataset': False,
            'custom_dataset_name': "bigset_train_data",
            'custom_training_data_location': '/storage-t1/database/bigset/train/data',
            'custom_type_of_image': 'bmp', # bmp, tif

            # (Training only) if not creating new dataset, input file name and type.
            # Will then train on this dataset
            'training_data_fileName': 'mnist', # 'Training_Data', 'bigset_train_data', special cases: 'mnist','cifar10','celeba'
            'training_data_type': 'npy', # mat, npy

            # (Testing only) if testing, use these parameters to define where and what type of images testing on
            'Testing_data_location': '/storage-t1/database/bigset/test',# '/storage-t1/database/bigset/test', # 'Set11'
            'testing_data_isFolderImages': True,
            'testing_data_type': 'bmp',  # bmp, tif
        }
    )
        