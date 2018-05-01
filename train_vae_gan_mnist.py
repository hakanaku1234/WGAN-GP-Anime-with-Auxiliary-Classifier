import argparse
parser = argparse.ArgumentParser(description='Music Generation with VAE')
parser.add_argument('--batch_size', type=int, default=16, required=False,
                    help='batch size')
parser.add_argument('--epochs', type=int, default=50, required=False,
                    help='epochs')
parser.add_argument('--std', type=float, default=1.0, required=False,
                    help='sampling std')
parser.add_argument('--use_sse', action='store_true', default=False,
                    help='')
args = parser.parse_args()

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import tensorflow as tf
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.Session(config=config)
import keras
from keras import backend as K
K.set_session(session)
from keras.models import *
from tools import *
from vae_model import build_residual_vae, build_vae_gan
from keras.datasets import mnist
from keras.callbacks import TensorBoard
from keras.callbacks import Callback
from skimage.io import imsave
from skimage.transform import resize
from tqdm import tqdm

BS = args.batch_size
EPOCHS = args.epochs
w, h, c = 28, 28, 1
latent_dim = 100
generator_model, discriminator_model, vae_model, encoder, decoder, discriminator = build_vae_gan(h=h, w=w, c=c, latent_dim=latent_dim, epsilon_std=args.std, batch_size=BS, dropout_rate=0.2, use_vae=True, vae_use_sse=args.use_sse)
(x_train, _), (___, __) = mnist.load_data()
# x_train = (np.asarray(list(map(lambda x: resize(x, (h,w), order=1, preserve_range=True), x_train)), dtype=np.float32)[...,np.newaxis] - 127.5) / 127.5
x_train = (x_train.astype(np.float32)[...,np.newaxis]-127.5) / 127.5

if not os.path.exists('./preview'):
    os.makedirs('./preview')

for epoch in range(EPOCHS):
    print("Epoch: %d / %d"%(epoch+1, EPOCHS))
    np.random.shuffle(x_train)
    with tqdm(total=int(np.ceil(float(len(x_train)) / BS))) as t:
        for i in range(0, len(x_train), BS):
            r_bound = min(len(x_train), i+BS)
            l_bound = r_bound - BS
            image_batch = x_train[l_bound:r_bound]
            noise = np.random.normal(0, args.std, (BS, latent_dim)).astype(np.float32)
            msg = ''
            msg += 'DL: {:.2f}, '.format(np.mean(discriminator_model.train_on_batch([image_batch, noise], None)))
            msg += 'GL: {:.2f}, '.format(np.mean(generator_model.train_on_batch(np.random.normal(0, args.std, (BS, latent_dim)).astype(np.float32), None)))
            msg += 'VAE_L: {:.2f} '.format(np.mean(vae_model.train_on_batch(image_batch, None)))
            t.set_description(msg)
            t.update()
    generate_images(decoder, './preview', h, w, c, latent_dim, args.std, 15, 15, epoch, BS)
    encoder.save('./encoder.h5')
    decoder.save('./decoder.h5')
    discriminator.save('./discriminator.h5')
