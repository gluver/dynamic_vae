# -*- coding: utf-8 -*-
# @Time : 2021/11/13 14:29
# @Author : huangshaobo，liujiachang,zhangyang                                                 
# @Email : sdk.eval@thinkenergy.net.cn
# @File : extract.py
import json
import os
import sys
import time
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from utils import collate
from model import dataset
from train import extract
from utils import to_var, collate, Normalizer, PreprocessNormalizer
from model import tasks
import pickle
import pandas as pd


class Extraction:

    def __init__(self, args):
        self.args = args

    def main(self):
        """
        Used for feature extraction
        test: Normalized test data is similar to train in train.py  
        task: Task, such as EvTask and JeveTask, is used to extract features of different dimensions  
        model: The trained model is the same as the model saved in train.py
        """
        model_params_path = os.path.join(self.args.current_model_path, "model_params.json")
        with open(model_params_path, 'r') as load_f:
            prams_dict = json.load(load_f)
        model_params = prams_dict['args']
        model_tag=prams_dict['train_time_start'].split('/')[1]
        start_time = time.time()
        data_pre = dataset.Dataset(model_params["test_path"],is_test=True)
        self.normalizer = pickle.load(open(os.path.join(self.args.current_model_path, "norm.pkl"), 'rb'))
        test = PreprocessNormalizer(data_pre, normalizer_fn=self.normalizer.norm_func)

        task = tasks.Task(task_name=model_params["task"], columns=model_params["columns"])

        # Open the saved model file
        model_torch = os.path.join(model_params["current_model_path"], "model.torch")
        model = to_var(torch.load(model_torch)).float()
        model.encoder_filter = task.encoder_filter
        model.decoder_filter = task.decoder_filter
        model.noise_scale = model_params["noise_scale"]
        data_loader = DataLoader(dataset=test, batch_size=model_params["batch_size"], shuffle=False,
                                 num_workers=model_params["jobs"], drop_last=False,                           
                                 pin_memory=torch.cuda.is_available(),
                                 collate_fn=collate if model_params["variable_length"] else None)

        print("sliding windows dataset length is: ", len(test))
        print("model", model)

        # Start extracting features using trained models
        
        model.eval()
        p_bar = tqdm(total=len(data_loader), desc='saving', ncols=100, mininterval=1, maxinterval=10, miniters=1)
        nll_losses=extract(data_loader, model, task, model_params["save_feature_path"], p_bar, model_params["noise_scale"],
                model_params["variable_length"],is_test=True)
        nll_losses=nll_losses.cpu().detach().numpy()
        p_bar.close()
        # Save scores to csv
        df=pd.DataFrame.from_dict({'file_name':os.listdir(model_params["test_path"]),'score':nll_losses})
        df.to_csv("result_"+model_tag+".csv",index=False)
        print("Anomoly detection socre saved at result.csv")
        # Save feature extration result
        print("Feature extraction of all test saved at", model_params["save_feature_path"])
        print("The total time consuming：", time.time() - start_time)


if __name__ == '__main__':
    import argparse

    os.environ["CUDA_VISIBLE_DEVICES"] = "1"
    parser = argparse.ArgumentParser(description='Train Example')
    parser.add_argument('--current_model_path', type=str,
                        default='/home/credog/GitRepos/dynamic_vae/PRETRAIN/2022-10-08-17-48-12/model/')
    args = parser.parse_args()
    Extraction(args).main()
