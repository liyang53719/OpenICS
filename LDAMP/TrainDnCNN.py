__author__ = 'cmetzler&alimousavi'
import numpy as np
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import time
import LearnedDAMP as LDAMP
from matplotlib import pyplot as plt
import h5py

parser = argparse.ArgumentParser()
parser.add_argument(
    "--debug",
    type=bool,
    nargs="?",
    const=True,
    default=False,
    help="Use debugger to track down bad values during training")
parser.add_argument(
    "--DnCNN_layers",
    type=int,
    default=16,
    help="How many DnCNN layers per network")
parser.add_argument(
    "--sigma_w_min",
    type=float,
    default=25.,
    help="Lowest noise level used to train network")
parser.add_argument(
    "--sigma_w_max",
    type=float,
    default=25.,
    help="Highest noise level used to train network")
parser.add_argument(
    "--loss_func",
    type=str,
    default="MSE",#Options are SURE or MSE
    help="Which loss function to use")
FLAGS, unparsed = parser.parse_known_args()

print(FLAGS)

## Network Parameters
height_img = 50#50
width_img = 50#50
channel_img = 1 # RGB -> 3, Grayscale -> 1
filter_height = 3
filter_width = 3
num_filters = 64
n_DnCNN_layers= FLAGS.DnCNN_layers


## Training Parameters
max_Epoch_Fails=3#How many training epochs to run without improvement in the validation error
ResumeTraining=False#Load weights from a network you've already trained a little
learning_rates = [0.001, 0.0001]#, 0.00001]
EPOCHS = 50
n_Train_Images=128*1600#3000
n_Val_Images=10000#Must be less than 21504
BATCH_SIZE = 128
loss_func=FLAGS.loss_func
if loss_func=='SURE':
    useSURE=True
else:
    useSURE=False

## Problem Parameters
sigma_w_min=FLAGS.sigma_w_min/255.#Noise std
sigma_w_max=FLAGS.sigma_w_max/255.#Noise std
n=channel_img*height_img*width_img

# Parameters to to initalize weights. Won't be used if old weights are loaded
init_mu = 0
init_sigma = 0.1

train_start_time=time.time()

## Clear all the old variables, tensors, etc.
#tf.reset_default_graph()

LDAMP.SetNetworkParams(new_height_img=height_img, new_width_img=width_img, new_channel_img=channel_img, \
                       new_filter_height=filter_height, new_filter_width=filter_width, new_num_filters=num_filters, \
                       new_n_DnCNN_layers=n_DnCNN_layers, new_n_DAMP_layers=None,
                       new_sampling_rate=None, \
                       new_BATCH_SIZE=BATCH_SIZE, new_sigma_w=None, new_n=n, new_m=None, new_training=True)
LDAMP.ListNetworkParameters()


# tf Graph input

#training_tf = tf.placeholder(tf.bool, name='training')
#sigma_w_tf = tf.placeholder(tf.float32)
#x_true = tf.placeholder(tf.float32, [n, BATCH_SIZE])
def test(training_tf, sigma_w_tf, x_true,dncnn, dncnnWrapper):
    y_measured = LDAMP.AddNoise(x_true,sigma_w_tf)
    theta_dncnn=LDAMP.init_vars_DnCNN(init_mu, init_sigma)
    [x_hat, div_overN] = LDAMP.DnCNN_wrapper(y_measured,None,theta_dncnn,dncnn,dncnnWrapper,training=training_tf)
    return [x_hat, div_overN, y_measured]

## Construct the measurement model and handles/placeholders
#y_measured = LDAMP.AddNoise(x_true,sigma_w_tf)

## Initialize the variable theta which stores the weights and biases
#theta_dncnn=LDAMP.init_vars_DnCNN(init_mu, init_sigma)

## Construct the reconstruction model
#x_hat = LDAMP.DnCNN(y_measured,None,theta_dncnn,training=training_tf)
#[x_hat, div_overN] = LDAMP.DnCNN_wrapper(y_measured,None,theta_dncnn,training=training_tf)

## Define loss and optimizer

nfp=np.float32(height_img*width_img)
def lossFunction(x_hat,div_overN,y_measured,sigma_w_tf):
    if useSURE:
        cost = LDAMP.MCSURE_loss(x_hat,div_overN,y_measured,sigma_w_tf)
    else:
        cost = LDAMP.MCSURE_loss(x_hat,div_overN,y_measured,sigma_w_tf)#cost = torch.nn.MSELoss(reduction='sum')###tf.nn.l2_loss(x_true-x_hat)* 1./ nfp

LDAMP.CountParameters()

## Load and Preprocess Training Data
#Training data was generated by GeneratingTrainingImages.m and ConvertImagestoNpyArrays.py
train_images = np.load('./TrainingData/TrainingData_patch'+str(height_img)+'.npy')
train_images=train_images[range(n_Train_Images),0,:,:]
assert (len(train_images)>=n_Train_Images), "Requested too much training data"

val_images = np.load('./TrainingData/ValidationData_patch'+str(height_img)+'.npy')
val_images=val_images[:,0,:,:]
assert (len(val_images)>=n_Val_Images), "Requested too much validation data"

x_train = np.transpose(np.reshape(train_images, (-1, channel_img * height_img * width_img)))
x_val = np.transpose(np.reshape(val_images, (-1, channel_img * height_img * width_img)))

## Train the Model
for learning_rate in learning_rates:
    dncnn = LDAMP.DnCNN()
    dncnnWrapper = LDAMP.DnCNN()
    lossfn = nn.MSELoss()
    optimizer = optim.Adam(dncnnWrapper.parameters(), lr =learning_rate)#optimizer0 = tf.train.AdamOptimizer(learning_rate=learning_rate) # Train all the variables
    #update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    #with tf.control_dependencies(update_ops):
        # Ensures that we execute the update_ops before performing the train_step. Allows us to update averages w/in BN
    #optimizer.zero_grad() #optimizer = optimizer0.minimize(cost)

    #outputs = net(x_train)
    #loss = cost(outputs, labels)
    #loss.backward()


    #saver_best = tf.train.Saver()  # defaults to saving all variables
    #saver_dict={}
    #with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
    #    sess.run(tf.global_variables_initializer())#Seems to be necessary for the batch normalization layers for some reason.

        # if FLAGS.debug:
        #     sess = tf_debug.LocalCLIDebugWrapperSession(sess)
        #     sess.add_tensor_filter("has_inf_or_nan", tf_debug.has_inf_or_nan)

    start_time = time.time()
        ###SAVER CODE 1
    
    print("Training ...")
    print()
    if __name__ == '__main__':
        #save_name = LDAMP.GenDnCNNFilename(sigma_w_min,sigma_w_max,useSURE=useSURE)
        #save_name_chckpt = save_name + ".ckpt"
        val_values = []
        print("Initial Weights Validation Value:")
        rand_inds = np.random.choice(len(val_images), n_Val_Images, replace=False)
        start_time = time.time()
        for offset in range(0, n_Val_Images - BATCH_SIZE + 1, BATCH_SIZE):  # Subtract batch size-1 to avoid eerrors when len(train_images) is not a multiple of the batch size
            end = offset + BATCH_SIZE

            batch_x_val = x_val[:, rand_inds[offset:end]]
            sigma_w_thisBatch = sigma_w_min + np.random.rand() * (sigma_w_max - sigma_w_min)

            [x_hat,div_overN, y_measured] = test(False, sigma_w_thisBatch, torch.from_numpy(batch_x_val), dncnn,dncnnWrapper)
            # Run optimization.
            loss_val = lossFunction(batch_x_val,div_overN,y_measured,sigma_w_thisBatch)     #sess.run(cost, feed_dict={x_true: batch_x_val, sigma_w_tf: sigma_w_thisBatch, training_tf:False})
            val_values.append(loss_val)
        time_taken = time.time() - start_time
        print(np.mean(val_values))
        best_val_error = np.mean(val_values)
        #best_sess = sess
        print("********************")
        #save_path = saver_best.save(best_sess, save_name_chckpt)
        #print("Initial session model saved in file: %s" % save_path)
        failed_epochs=0
        for i in range(EPOCHS):
            if failed_epochs>=max_Epoch_Fails:
                break
            train_values = []
            print ("This Training iteration ...")
            rand_inds=np.random.choice(len(train_images), n_Train_Images,replace=False)
            start_time = time.time()
            for offset in range(0, n_Train_Images-BATCH_SIZE+1, BATCH_SIZE):#Subtract batch size-1 to avoid errors when len(train_images) is not a multiple of the batch size
                end = offset + BATCH_SIZE

                batch_x_train = x_train[:, rand_inds[offset:end]]
                sigma_w_thisBatch = sigma_w_min+np.random.rand()*(sigma_w_max-sigma_w_min)

                # Run optimization.
                _, loss_val = sess.run([optimizer,cost], feed_dict={x_true: batch_x_train, sigma_w_tf: sigma_w_thisBatch, training_tf:True})#Feed dict names should match with the placeholders
                train_values.append(loss_val)
            time_taken = time.time() - start_time
            print(np.mean(train_values))
            val_values = []
            print("EPOCH ",i+1," Validation Value:" )
            rand_inds = np.random.choice(len(val_images), n_Val_Images, replace=False)
            start_time = time.time()
            for offset in range(0, n_Val_Images-BATCH_SIZE+1, BATCH_SIZE):#Subtract batch size-1 to avoid eerrors when len(train_images) is not a multiple of the batch size
                end = offset + BATCH_SIZE

                batch_x_val = x_val[:, rand_inds[offset:end]]
                sigma_w_thisBatch = sigma_w_min + np.random.rand() * (sigma_w_max - sigma_w_min)

                # Run optimization.
                loss_val = sess.run(cost, feed_dict={x_true: batch_x_val, sigma_w_tf: sigma_w_thisBatch, training_tf:False})
                val_values.append(loss_val)
            time_taken = time.time() - start_time
            print(np.mean(val_values))
            if(np.mean(val_values) < best_val_error):
                failed_epochs=0
                best_val_error = np.mean(val_values)
                best_sess = sess
                print("********************")
                save_path = saver_best.save(best_sess, save_name_chckpt)
                print("Best session model saved in file: %s" % save_path)
            else:
                failed_epochs=failed_epochs+1
            print("********************")

total_train_time=time.time()-train_start_time
#save_name_time = save_name + "_time.txt"
#f= open(save_name, 'wb')
#f.write("Total Training Time ="+str(total_train_time))
#f.close()
