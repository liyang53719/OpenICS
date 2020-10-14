import sensing_methods
import utils

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import os
import glob
from time import time
from torch.nn import init
import cv2
from skimage.measure import compare_ssim as ssim
from argparse import ArgumentParser

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = '0'
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def reconstruction_method(reconstruction, specifics):
    # a function to return the reconstruction method with given parameters. It's a class with two methods: initialize and run.
    ISTANetPLus_model = ISTANetPlus_wrapper(specifics)
    return ISTANetPLus_model


class ISTANetPlus_wrapper():
    def __init__(self,specifics):
        # do the initialization of the network with given parameters.
        self.specifics = specifics

    def initialize(self,dataset,sensing):
        # do the preparation for the running.
        self.rand_loader = dataset

    def run(self):
        if (self.specifics['stage'] == 'training'):
            model = ISTANetplus(self.specifics['layer_num'])
            model = nn.DataParallel(model)
            model = model.to(device)

            start_epoch = self.specifics['start_epoch']
            end_epoch = self.specifics['end_epoch']
            learning_rate = self.specifics['learning_rate']
            layer_num = self.specifics['layer_num']
            group_num = self.specifics['group_num']
            cs_ratio = self.specifics['cs_ratio']
            gpu_list = self.specifics['gpu_list']
            batch_size = self.specifics['batch_size']
            nrtrain = self.specifics['nrtrain']
            model_dir = self.specifics['model_dir']
            log_dir = self.specifics['log_dir']

            print_flag = 1  # print parameter number

            if print_flag:
                num_count = 0
                for para in model.parameters():
                    num_count += 1
                    print('Layer %d' % num_count)
                    print(para.size())

            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

            model_dir = "./%s/CS_ISTA_Net_plus_layer_%d_group_%d_ratio_%d_lr_%.4f" % (
            model_dir, layer_num, group_num, cs_ratio, learning_rate)

            log_file_name = "./%s/Log_CS_ISTA_Net_plus_layer_%d_group_%d_ratio_%d_lr_%.4f.txt" % (
            log_dir, layer_num, group_num, cs_ratio, learning_rate)

            if not os.path.exists(model_dir):
                os.makedirs(model_dir)

            if start_epoch > 0:
                pre_model_dir = model_dir
                model.load_state_dict(torch.load('./%s/net_params_%d.pkl' % (pre_model_dir, start_epoch)))

            Training_labels = utils.getTrainingLabels(self.specifics['stage'], self.specifics)
            Phi_input, Qinit = sensing_methods.computInitMx(Training_labels=Training_labels, specifics=self.specifics)

            Phi = torch.from_numpy(Phi_input).type(torch.FloatTensor)
            Phi = Phi.to(device)

            Qinit = torch.from_numpy(Qinit).type(torch.FloatTensor)
            Qinit = Qinit.to(device)

            # Training loop
            print('Training on GPU? ' + str(torch.cuda.is_available()))
            for epoch_i in range(start_epoch + 1, end_epoch + 1):
                for j, data in enumerate(self.rand_loader):

                    batch_x = data
                    batch_x = batch_x.to(device)

                    Phix = torch.mm(batch_x, torch.transpose(Phi, 0, 1))

                    [x_output, loss_layers_sym] = model(Phix, Phi, Qinit)

                    # Compute and print loss
                    loss_discrepancy = torch.mean(torch.pow(x_output - batch_x, 2))

                    loss_constraint = torch.mean(torch.pow(loss_layers_sym[0], 2))
                    for k in range(layer_num - 1):
                        loss_constraint += torch.mean(torch.pow(loss_layers_sym[k + 1], 2))

                    gamma = torch.Tensor([0.01]).to(device)

                    # loss_all = loss_discrepancy
                    loss_all = loss_discrepancy + torch.mul(gamma, loss_constraint)

                    # Zero gradients, perform a backward pass, and update the weights.
                    optimizer.zero_grad()
                    loss_all.backward()
                    optimizer.step()

                    output_data = "[%02d/%02d][%d/%d] Total Loss: %.4f, Discrepancy Loss: %.4f,  Constraint Loss: %.4f\n" % (
                    epoch_i, end_epoch, j * batch_size, nrtrain, loss_all.item(), loss_discrepancy.item(),
                    loss_constraint)
                    print(output_data)

                output_file = open(log_file_name, 'a')
                output_file.write(output_data)
                output_file.close()

                if epoch_i % 5 == 0:
                    torch.save(model.state_dict(),
                               "./%s/net_params_%d.pkl" % (model_dir, epoch_i))  # save only the parameters
        elif (self.specifics['stage'] == 'testing'):
            model = ISTANetplus(self.specifics['layer_num'])
            model = nn.DataParallel(model)
            model = model.to(device)

            epoch_num = self.specifics['testing_epoch_num']
            learning_rate = self.specifics['learning_rate']
            layer_num = self.specifics['layer_num']
            group_num = self.specifics['group_num']
            cs_ratio = self.specifics['cs_ratio']
            model_dir = self.specifics['model_dir']
            log_dir = self.specifics['log_dir']
            data_dir = self.specifics['data_dir']
            result_dir = self.specifics['result_dir']
            test_name = self.specifics['test_name']

            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

            model_dir = "./%s/CS_ISTA_Net_plus_layer_%d_group_%d_ratio_%d_lr_%.4f" % (
            model_dir, layer_num, group_num, cs_ratio, learning_rate)

            # Load pre-trained model with epoch number
            model.load_state_dict(torch.load('./%s/net_params_%d.pkl' % (model_dir, epoch_num)))

            test_dir = os.path.join(data_dir, test_name)
            filepaths = glob.glob(test_dir + '/*.tif')

            result_dir = os.path.join(result_dir, test_name)
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)

            ImgNum = len(filepaths)
            PSNR_All = np.zeros([1, ImgNum], dtype=np.float32)
            SSIM_All = np.zeros([1, ImgNum], dtype=np.float32)

            Training_labels = 0 # not needed for testing
            Phi_input, Qinit = sensing_methods.computInitMx(Training_labels=Training_labels, specifics=self.specifics)

            Phi = torch.from_numpy(Phi_input).type(torch.FloatTensor)
            Phi = Phi.to(device)

            Qinit = torch.from_numpy(Qinit).type(torch.FloatTensor)
            Qinit = Qinit.to(device)

            print('\n')
            print("CS Reconstruction Start")

            with torch.no_grad():
                for img_no in range(ImgNum):
                    imgName = filepaths[img_no]

                    Img = cv2.imread(imgName, 1)

                    Img_yuv = cv2.cvtColor(Img, cv2.COLOR_BGR2YCrCb)
                    Img_rec_yuv = Img_yuv.copy()

                    Iorg_y = Img_yuv[:, :, 0]

                    [Iorg, row, col, Ipad, row_new, col_new] = utils.imread_CS_py(Iorg_y)
                    Icol = utils.img2col_py(Ipad, 33).transpose() / 255.0

                    Img_output = Icol

                    start = time()

                    batch_x = torch.from_numpy(Img_output)
                    batch_x = batch_x.type(torch.FloatTensor)
                    batch_x = batch_x.to(device)

                    Phix = torch.mm(batch_x, torch.transpose(Phi, 0, 1))

                    [x_output, loss_layers_sym] = model(Phix, Phi, Qinit)

                    end = time()

                    Prediction_value = x_output.cpu().data.numpy()

                    # loss_sym = torch.mean(torch.pow(loss_layers_sym[0], 2))
                    # for k in range(layer_num - 1):
                    #     loss_sym += torch.mean(torch.pow(loss_layers_sym[k + 1], 2))
                    #
                    # loss_sym = loss_sym.cpu().data.numpy()

                    X_rec = np.clip(utils.col2im_CS_py(Prediction_value.transpose(), row, col, row_new, col_new), 0, 1)

                    rec_PSNR = utils.psnr(X_rec * 255, Iorg.astype(np.float64))
                    rec_SSIM = ssim(X_rec * 255, Iorg.astype(np.float64), data_range=255)

                    print("[%02d/%02d] Run time for %s is %.4f, PSNR is %.2f, SSIM is %.4f" % (
                    img_no, ImgNum, imgName, (end - start), rec_PSNR, rec_SSIM))

                    Img_rec_yuv[:, :, 0] = X_rec * 255

                    im_rec_rgb = cv2.cvtColor(Img_rec_yuv, cv2.COLOR_YCrCb2BGR)
                    im_rec_rgb = np.clip(im_rec_rgb, 0, 255).astype(np.uint8)

                    resultName = imgName.replace(data_dir, result_dir)
                    cv2.imwrite("%s_ISTA_Net_plus_ratio_%d_epoch_%d_PSNR_%.2f_SSIM_%.4f.png" % (
                    resultName, cs_ratio, epoch_num, rec_PSNR, rec_SSIM), im_rec_rgb)
                    del x_output

                    PSNR_All[0, img_no] = rec_PSNR
                    SSIM_All[0, img_no] = rec_SSIM

            print('\n')
            output_data = "CS ratio is %d, Avg PSNR/SSIM for %s is %.2f/%.4f, Epoch number of model is %d \n" % (
            cs_ratio, test_name, np.mean(PSNR_All), np.mean(SSIM_All), epoch_num)
            print(output_data)

            output_file_name = "./%s/PSNR_SSIM_Results_CS_ISTA_Net_plus_layer_%d_group_%d_ratio_%d_lr_%.4f.txt" % (
            log_dir, layer_num, group_num, cs_ratio, learning_rate)

            output_file = open(output_file_name, 'a')
            output_file.write(output_data)
            output_file.close()

            print("CS Reconstruction End")

# Define ISTA-Net-plus Block
class BasicBlock(torch.nn.Module):
    def __init__(self):
        super(BasicBlock, self).__init__()

        self.lambda_step = nn.Parameter(torch.Tensor([0.5]))
        self.soft_thr = nn.Parameter(torch.Tensor([0.01]))

        self.conv_D = nn.Parameter(init.xavier_normal_(torch.Tensor(32, 1, 3, 3)))

        self.conv1_forward = nn.Parameter(init.xavier_normal_(torch.Tensor(32, 32, 3, 3)))
        self.conv2_forward = nn.Parameter(init.xavier_normal_(torch.Tensor(32, 32, 3, 3)))
        self.conv1_backward = nn.Parameter(init.xavier_normal_(torch.Tensor(32, 32, 3, 3)))
        self.conv2_backward = nn.Parameter(init.xavier_normal_(torch.Tensor(32, 32, 3, 3)))

        self.conv_G = nn.Parameter(init.xavier_normal_(torch.Tensor(1, 32, 3, 3)))

    def forward(self, x, PhiTPhi, PhiTb):
        x = x - self.lambda_step * torch.mm(x, PhiTPhi)
        x = x + self.lambda_step * PhiTb
        x_input = x.view(-1, 1, 33, 33)

        x_D = F.conv2d(x_input, self.conv_D, padding=1)

        x = F.conv2d(x_D, self.conv1_forward, padding=1)
        x = F.relu(x)
        x_forward = F.conv2d(x, self.conv2_forward, padding=1)

        x = torch.mul(torch.sign(x_forward), F.relu(torch.abs(x_forward) - self.soft_thr))

        x = F.conv2d(x, self.conv1_backward, padding=1)
        x = F.relu(x)
        x_backward = F.conv2d(x, self.conv2_backward, padding=1)

        x_G = F.conv2d(x_backward, self.conv_G, padding=1)

        x_pred = x_input + x_G

        x_pred = x_pred.view(-1, 1089)

        x = F.conv2d(x_forward, self.conv1_backward, padding=1)
        x = F.relu(x)
        x_D_est = F.conv2d(x, self.conv2_backward, padding=1)
        symloss = x_D_est - x_D

        return [x_pred, symloss]


# Define ISTA-Net-plus
class ISTANetplus(torch.nn.Module):
    def __init__(self, LayerNo):
        super(ISTANetplus, self).__init__()
        onelayer = []
        self.LayerNo = LayerNo

        for i in range(LayerNo):
            onelayer.append(BasicBlock())

        self.fcs = nn.ModuleList(onelayer)

    def forward(self, Phix, Phi, Qinit):

        PhiTPhi = torch.mm(torch.transpose(Phi, 0, 1), Phi)
        PhiTb = torch.mm(Phix, Phi)

        x = torch.mm(Phix, torch.transpose(Qinit, 0, 1))

        layers_sym = []   # for computing symmetric loss

        for i in range(self.LayerNo):
            [x, layer_sym] = self.fcs[i](x, PhiTPhi, PhiTb)
            layers_sym.append(layer_sym)

        x_final = x

        return [x_final, layers_sym]
