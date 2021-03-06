#! /usr/bin/env python
#
# Copyright (C) 2015-2016 Rich Lewis <rl403@cam.ac.uk>
# License: 3-clause BSD

"""
## skchem.descriptors.atom

Module specifying atom based descriptor generators.
"""

import functools
from abc import ABCMeta

import pandas as pd
import numpy as np

from rdkit import Chem
from rdkit.Chem import Crippen
from rdkit.Chem import Lipinski
from rdkit.Chem import rdMolDescriptors, rdPartialCharges
from rdkit.Chem.rdchem import HybridizationType

from ..core import Mol
from ..resource import PERIODIC_TABLE, ORGANIC
from ..base import AtomTransformer, Featurizer
from ..utils import nanarray


def element(a):

    """ Return the element """

    return a.GetSymbol()


def is_element(a, symbol='C'):

    """ Is the atom of a given element """
    return element(a) == symbol

element_features = {'is_{}'.format(e): functools.partial(is_element, symbol=e)
                    for e in ORGANIC}


def is_h_acceptor(a):

    """ Is an H acceptor? """

    m = a.GetOwningMol()
    idx = a.GetIdx()
    return idx in [i[0] for i in Lipinski._HAcceptors(m)]


def is_h_donor(a):

    """ Is an H donor? """

    m = a.GetOwningMol()
    idx = a.GetIdx()
    return idx in [i[0] for i in Lipinski._HDonors(m)]


def is_hetero(a):

    """ Is a heteroatom? """

    m = a.GetOwningMol()
    idx = a.GetIdx()
    return idx in [i[0] for i in Lipinski._Heteroatoms(m)]


def atomic_number(a):

    """ Atomic number of atom """

    return a.GetAtomicNum()


def atomic_mass(a):

    """ Atomic mass of atom """

    return a.atomic_mass


def explicit_valence(a):

    """ Explicit valence of atom """
    return a.GetExplicitValence()


def implicit_valence(a):

    """ Implicit valence of atom """

    return a.GetImplicitValence()


def valence(a):

    """ returns the valence of the atom """

    return explicit_valence(a) + implicit_valence(a)


def formal_charge(a):

    """ Formal charge of atom """

    return a.GetFormalCharge()


def is_aromatic(a):

    """ Boolean if atom is aromatic"""

    return a.GetIsAromatic()


def num_implicit_hydrogens(a):

    """ Number of implicit hydrogens """

    return a.GetNumImplicitHs()


def num_explicit_hydrogens(a):

    """ Number of explicit hydrodgens """

    return a.GetNumExplicitHs()


def num_hydrogens(a):

    """ Number of hydrogens """

    return num_implicit_hydrogens(a) + num_explicit_hydrogens(a)


def is_in_ring(a):

    """ Whether the atom is in a ring """

    return a.IsInRing()


def crippen_log_p_contrib(a):

    """ Hacky way of getting logP contribution. """

    idx = a.GetIdx()
    m = a.GetOwningMol()
    return Crippen._GetAtomContribs(m)[idx][0]


def crippen_molar_refractivity_contrib(a):

    """ Hacky way of getting molar refractivity contribution. """

    idx = a.GetIdx()
    m = a.GetOwningMol()
    return Crippen._GetAtomContribs(m)[idx][1]


def tpsa_contrib(a):

    """ Hacky way of getting total polar surface area contribution. """

    idx = a.GetIdx()
    m = a.GetOwningMol()
    return rdMolDescriptors._CalcTPSAContribs(m)[idx]


def labute_asa_contrib(a):

    """ Hacky way of getting accessible surface area contribution. """

    idx = a.GetIdx()
    m = a.GetOwningMol()
    return rdMolDescriptors._CalcLabuteASAContribs(m)[0][idx]


def gasteiger_charge(a, force_calc=False):

    """ Hacky way of getting gasteiger charge """

    res = a.props.get('_GasteigerCharge', None)
    if res and not force_calc:
        return float(res)
    else:
        m = a.GetOwningMol()
        rdPartialCharges.ComputeGasteigerCharges(m)
        return float(a.props['_GasteigerCharge'])


def pauling_electronegativity(a):

    return a.pauling_electronegativity


def first_ionization(a):

    return PERIODIC_TABLE.loc[a.atomic_number, 'first_ionisation_energy']


def group(a):

    return PERIODIC_TABLE.loc[a.atomic_number, 'group']


def period(a):

    return PERIODIC_TABLE.loc[a.atomic_number, 'period']


def is_hybridized(a, hybrid_type=HybridizationType.SP3):

    """ Hybridized as type hybrid_type, default SP3 """

    return str(a.GetHybridization()) == str(hybrid_type)

hybridization_features = {'is_' + n + '_hybridized': functools.partial(
    is_hybridized, hybrid_type=n)
                          for n in HybridizationType.names}

ATOM_FEATURES = {
    'atomic_number': atomic_number,
    'atomic_mass': atomic_mass,
    'formal_charge': formal_charge,
    'gasteiger_charge': gasteiger_charge,
    'pauling_electronegativity': pauling_electronegativity,
    'first_ionisation': first_ionization,
    'group': group,
    'period': period,
    'valence': valence,
    'is_aromatic': is_aromatic,
    'num_hydrogens': num_hydrogens,
    'is_in_ring': is_in_ring,
    'log_p_contrib': crippen_log_p_contrib,
    'molar_refractivity_contrib': crippen_molar_refractivity_contrib,
    'is_h_acceptor': is_h_acceptor,
    'is_h_donor': is_h_donor,
    'is_heteroatom': is_hetero,
    'total_polar_surface_area_contrib': tpsa_contrib,
    'total_labute_accessible_surface_area': labute_asa_contrib,
}
ATOM_FEATURES.update(element_features)
ATOM_FEATURES.update(hybridization_features)


class AtomFeaturizer(AtomTransformer, Featurizer):

    def __init__(self, features='all', n_jobs=1, verbose=True):
        self._features = None
        self.features = features

        super(AtomFeaturizer, self).__init__(n_jobs=n_jobs, verbose=verbose)

    @property
    def name(self):
        return 'atom_feat'

    @property
    def features(self):
        return self._features

    @features.setter
    def features(self, features):
        if isinstance(features, str):
            if features == 'all':
                features = ATOM_FEATURES
            else:
                features = {features: ATOM_FEATURES[features]}
        elif isinstance(features, list):
            features = {feature: ATOM_FEATURES[feature]
                        for feature in features}
        elif isinstance(features, (dict, pd.Series)):
            features = features
        else:
            raise NotImplementedError('Cannot use features {}'.format(
                features))

        self._features = pd.Series(features)
        self._features.index.name = 'atom_features'

    @property
    def minor_axis(self):
        return self.features.index

    def _transform_atom(self, atom):
        return self.features.apply(lambda f: f(atom)).values

    def _transform_mol(self, mol):
        return np.array([self.transform(a) for a in mol.atoms])


class DistanceTransformer(AtomTransformer, Featurizer):

    """ Base class implementing Distance Matrix transformers.

    Concrete classes inheriting from this should implement `_transform_mol`.
    """

    __metaclass__ = ABCMeta

    @property
    def minor_axis(self):
        return pd.RangeIndex(self.max_atoms, name='atom_idx')

    def _transform_atom(self, atom):
        return NotImplemented

    def transform(self, mols):
        res = super(DistanceTransformer, self).transform(mols)
        if isinstance(mols, Mol):
            res = res.iloc[:len(mols.atoms), :len(mols.atoms)]
        return res


class SpacialDistanceTransformer(DistanceTransformer):

    """ Transformer class for generating 3D distance matrices.  """

    # TODO: handle multiple conformers

    def __init__(self, n_jobs=1, verbose=True):

        """ Initialize a SpacialDistanceTransformer.

        Args:
            n_jobs (int):
                The number of processes to run the featurizer in.
            verbose (bool):
                Whether to output a progress bar.
        """
        super(SpacialDistanceTransformer, self).__init__(n_jobs=n_jobs,
                                                         verbose=verbose)

    @property
    def name(self):
        return 'spacial_dist'

    def _transform_mol(self, mol):
        res = nanarray((len(mol.atoms), self.max_atoms))
        res[:, :len(mol.atoms)] = Chem.Get3DDistanceMatrix(mol)
        return res


class GraphDistanceTransformer(DistanceTransformer):

    """ Transformer class for generating Graph distance matrices. """

    def __init__(self, n_jobs=1, verbose=True):

        """ Initialize a GraphDistanceTransformer.

        Args:
            n_jobs (int):
                The number of processes to run the featurizer in.
            verbose (bool):
                Whether to output a progress bar.
        """

        super(GraphDistanceTransformer, self).__init__(n_jobs=n_jobs,
                                                       verbose=verbose)

    @property
    def name(self):
        return 'graph_dist'

    def _transform_mol(self, mol):
        res = nanarray((len(mol.atoms), self.max_atoms))
        res[:len(mol.atoms), :len(mol.atoms)] = Chem.GetDistanceMatrix(mol)
        return res
