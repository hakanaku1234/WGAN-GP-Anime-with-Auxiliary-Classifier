import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.Session(config=config)
import keras
from keras import backend as K
K.set_session(session)
from keras.models import *
from models import up_bilinear
from es_base import ES
from skimage.io import imsave, imread
from skimage.transform import resize
from pixel_shuffler import PixelShuffler
import argparse

parser = argparse.ArgumentParser(description='Image Generation with GAN')
parser.add_argument('input', metavar='input', type=str, help='')
parser.add_argument('output', metavar='output', type=str, help='')
parser.add_argument('--decoder', type=str, default='./decoder.h5', required=False, help='decoder')
parser.add_argument('--encoder', type=str, default='./encoder.h5', required=False, help='encoder')
parser.add_argument('--std', type=float, default=0.1, required=False, help='')
parser.add_argument('--iterations', type=int, default=500, required=False, help='')
parser.add_argument('--populations', type=int, default=500, required=False, help='')
parser.add_argument('--offsprings', type=int, default=200, required=False, help='')
parser.add_argument('--runs', type=int, default=10, required=False, help='')
args = parser.parse_args()

decoder = load_model(args.decoder, custom_objects={'tf':tf, 'PixelShuffler':PixelShuffler, 'up_bilinear':up_bilinear})
encoder = load_model(args.encoder, custom_objects={'tf':tf, 'PixelShuffler':PixelShuffler, 'up_bilinear':up_bilinear}) if os.path.exists(args.encoder) else None
img = (resize(imread(args.input), decoder.output_shape[-3:-1], preserve_range=True).astype(np.float32) - 127.5) / 127.5
if img.ndim==2:
    img = img[...,np.newaxis]
def Fitness(img, decoder):
    def mse(x):
        return np.mean(np.square(img[np.newaxis,...]-decoder.predict(x)).reshape(x.shape[0], -1), axis=-1)
    return mse
if not encoder is None:
    x_mean = encoder.predict(img[np.newaxis,...])
es = ES(fitness=Fitness(img, decoder), dna_length=decoder.input_shape[-1], bound=[-args.std*2.0, args.std*2.0], generations=args.iterations, 
        population_size=args.populations, offspring_size=args.offsprings, type='minimize')
best_img = None
best_z = None
best_score = -1
for i in range(args.runs):
    print('Runs: %d / %d'%(i+1, args.runs))
    if encoder is None:
        pop = es.initialization()
    else:
        x_mutate = np.random.randn(args.populations, *x_mean.shape[1:]) * args.std
        pop = dict(DNA=x_mean.repeat(args.populations, axis=0), mut_strength=x_mutate)
    for ite in range(args.iterations):
        kids = es.get_offspring(pop)
        pop = es.put_kids(pop, kids)
        pop = es.selection(pop)
        print('iteration: {:d}/{:d}'.format(ite+1, args.iterations))
    z = pop['DNA'][-1]
    img_reconstruct = decoder.predict(z[np.newaxis,...])[0]
    mse = np.mean(np.square(img_reconstruct-img))
    print('mse: {:.2f}'.format(mse))
    if mse>best_score:
        best_score = mse
        best_z = z
        best_img = img_reconstruct
    output_img = np.round(np.concatenate((np.squeeze(img), np.squeeze(img_reconstruct)), axis=1) * 127.5 + 127.5).astype(np.uint8)
    filename, ext = os.path.splitext(args.output)
    imsave(filename+'_%d'%i+ext, output_img)
output_img = np.round(np.concatenate((np.squeeze(img), np.squeeze(best_img)), axis=1) * 127.5 + 127.5).astype(np.uint8)
imsave(args.output, output_img)