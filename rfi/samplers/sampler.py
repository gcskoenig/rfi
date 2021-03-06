"""Sampler can be used sample perturbed versions of a variable
conditional on a set G.

More details can be found in the class description
"""
import numpy as np
import pandas as pd

import rfi.utils as utils
from rfi.samplers._utils import sample_id  # , sample_perm
import logging
from typing import Union, List

logger = logging.getLogger(__name__)


class Sampler:
    """Can be used to resample perturbed versions of a variable conditional on
    any set of variables G.

    Attributes:
        X_train: reference to training data.
        cat_inputs: List of indices of categorical features, if None - considering all the features as continuous
        _trained_sampling_funcs: dictionary with (fsoi, G) as key and callable sampler as value
    """

    def __init__(self, X_train, cat_inputs: List[int] = None, **kwargs):
        """Initialize Sampler with X_train and mask."""
        self.X_train = X_train
        self.cat_inputs = self._to_array(cat_inputs if cat_inputs is not None else [])
        self._trained_sampling_funcs = {}
        self._trained_estimators = {}

        logger.info(f'Sampler initialized. Using following features as categorical {self.cat_inputs}')

    @staticmethod
    def _to_key(S):
        """
        Converts array to key for trainedGs Dict
        """
        return utils.fnames_to_key(S)

    @staticmethod
    def _to_array(S):
        """Coverts to numpy array of strings
        """
        return np.array(S).reshape(-1)

    @staticmethod
    def _order_fset(S):
        return sorted(S)

    @staticmethod
    def _pd_to_np(df):
        np_arr = df[sorted(df.columns)].to_numpy()
        return np.arr

    def is_trained(self, J, G):
        """Indicates whether the Sampler has been trained
        on a specific RFI set G for features J.

        Args:
            G: RFI set G to be checked

        Returns:
            Whether the sampler was trained with respect to
            a set G.

        """
        G_key, J_key = Sampler._to_key(G), Sampler._to_key(J)  # transform into hashable form
        trained = (J_key, G_key) in self._trained_sampling_funcs
        return trained

    def _train_J_degenerate(self, J, G, verbose=True):
        """Training function that takes care of degenerate cases
        where either j is in G or G is empty.
        Args:
            J: features of interest
            G: relative feature set

        Returns:
            Whether a degenerate case was present.
        """
        degenerate = True

        # are we conditioning on zero elements?
        # if G.size == 0:
        #     logger.debug('Degenerate Training: Empty G')
        #     J_ixs = utils.fset_to_ix(self.X_train.columns, J)
        #     self._store_samplefunc(J, G, sample_perm(J_ixs))
        # are all elements in G being conditioned upon?
        if np.sum(1 - np.isin(J, G)) == 0:
            logger.debug('Degenerate Training: J subseteq G')
            J_ixs = utils.fset_to_ix(Sampler._order_fset(G),
                                     Sampler._order_fset(J))
            self._store_samplefunc(J, G, sample_id(J_ixs))
        else:
            logger.debug('Training not degenerate.')
            degenerate = False

        return degenerate

    def _store_samplefunc(self, J, G, samplefunc, verbose=True):
        """Storing a trained sample function

        Args:
            samplefunc: function
            J: features of interest
            G: relative feature set
            verbose: printing or not
        """
        G_key, J_key = Sampler._to_key(G), Sampler._to_key(J)
        self._trained_sampling_funcs[(J_key, G_key)] = samplefunc
        logger.info('Training ended. Sampler saved.')

    def train(self, J, G, verbose=True):
        """Trains sampler using the training dataset to resample
        relative to any variable set G.

        Args:
            J: set of features to train on
            G: arbitrary set of variables.

        Returns:
            Nothing. Now the sample function can be used
            to resample on seen or unseen data.
        """
        logger.info('Training Sampler for: {} | {}'.format(J, G))

    def sample(self, X_test, J, G, num_samples=1):
        """Sample features of interest using trained resampler.

        Args:
            J: Set of features to sample
            G: relative feature set
            X_test: DataFrame for which sampling shall be performed
            num_samples: number of resamples without
                retraining shall be computed

        Returns:
            Resampled data for the features of interest.
            pd.DataFrame with multiindex ('sample', 'i')
            and resampled features as columns
        """
        # initialize numpy matrix
        # sampled_data = np.zeros((X_test.shape[0], num_samples, J.shape[0]))

        # sample
        G_key, J_key = Sampler._to_key(G), Sampler._to_key(J)

        if not self.is_trained(J, G):
            raise RuntimeError("Sampler not trained on {} | {}".format(J, G))
        else:
            sample_func = self._trained_sampling_funcs[(J_key, G_key)]
            smpl = sample_func(X_test[Sampler._order_fset(G)].to_numpy(),
                               num_samples=num_samples)
            snrs = np.arange(num_samples)
            obs = np.arange(X_test.shape[0])
            vss = [snrs, obs]
            ns = ['sample', 'i']
            index = utils.create_multiindex(ns, vss)

            smpl = np.swapaxes(smpl, 0, 1)
            smpl = smpl.reshape((-1, smpl.shape[2]))

            df = pd.DataFrame(smpl, index=index,
                              columns=Sampler._order_fset(J))
            return df
