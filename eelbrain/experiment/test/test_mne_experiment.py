# Author: Christian Brodbeck <christianbrodbeck@nyu.edu>
from nose.tools import eq_, assert_raises
import numpy as np
from numpy.testing import assert_equal

from eelbrain import Dataset, Factor, Var, MneExperiment
from ..._utils.testing import assert_dataobj_equal


class EventExperiment(MneExperiment):

    trigger_shift = 0.03

    variables = {'name': {1: 'Leicester', 2: 'Tilsit', 3: 'Caerphilly',
                          4: 'Bel Paese'},
                 'backorder': {(4, 4): 'no', (2, 3): 'yes'},
                 'taste': {(1, 2): 'good', 'default': 'bad'}}

    defaults = {'experiment': 'cheese',
                'model': 'name'}


SUBJECT = 'CheeseMonger'
SFREQ = 1000.
TRIGGERS = np.tile(np.arange(1, 5), 2)
I_START = np.arange(1001, 1441, 55)


def gen_triggers():
    raw = Var([], info={'sfreq': SFREQ})
    ds = Dataset(info={'subject': SUBJECT, 'raw': raw})
    ds['trigger'] = Var(TRIGGERS)
    ds['i_start'] = Var(I_START)
    return ds


def test_mne_experiment_templates():
    "Test MneExperiment template formatting"
    e = MneExperiment('', False)

    # Don't create dirs without root
    assert_raises(IOError, e.get, 'raw-file', mkdir=True)

    # compounds
    eq_(e.get('src-kind'), 'clm bestreg free-3-dSPM')
    e.set_inv('fixed')
    eq_(e.get('src-kind'), 'clm bestreg fixed-3-dSPM')
    e.set(cov='noreg')
    eq_(e.get('src-kind'), 'clm noreg fixed-3-dSPM')
    e.set(raw='0-40')
    eq_(e.get('src-kind'), '0-40 noreg fixed-3-dSPM')

    # inv
    e.set_inv('free', 3, 'dSPM', .8, True)
    eq_(e.get('inv'), 'free-3-dSPM-0.8-pick_normal')
    eq_(e._params['make_inv_kw'], {'loose': 1})
    eq_(e._params['apply_inv_kw'], {'method': 'dSPM', 'lambda2': 1. / 3**2})
    e.set_inv('fixed', 2, 'MNE', pick_normal=True)
    eq_(e.get('inv'), 'fixed-2-MNE-pick_normal')
    eq_(e._params['make_inv_kw'], {'fixed': True, 'loose': None})
    eq_(e._params['apply_inv_kw'], {'method': 'MNE', 'lambda2': 1. / 2**2,
                                    'pick_normal': True})
    e.set_inv(0.5, 3, 'sLORETA')
    eq_(e.get('inv'), 'loose.5-3-sLORETA')
    eq_(e._params['make_inv_kw'], {'loose': 0.5})
    eq_(e._params['apply_inv_kw'], {'method': 'sLORETA', 'lambda2': 1. / 3**2})


def test_test_experiment():
    "Test event labeling with the EventExperiment subclass of MneExperiment"
    e = EventExperiment('', False)

    # test defaults
    eq_(e.get('experiment'), 'cheese')
    eq_(e.get('model'), 'name')

    # test event labeling
    ds = e.label_events(gen_triggers())
    name = Factor([e.variables['name'][t] for t in TRIGGERS], name='name')
    assert_dataobj_equal(ds['name'], name)
    tgt = ds['trigger'].as_factor(e.variables['backorder'], 'backorder')
    assert_dataobj_equal(ds['backorder'], tgt)
    tgt = ds['trigger'].as_factor(e.variables['taste'],'taste')
    assert_dataobj_equal(ds['taste'], tgt)
    assert_equal(ds['i_start'], I_START + round((0.03 * SFREQ)))
    assert_equal(ds['subject'] == SUBJECT, True)
    # test without trigger shift
    e.trigger_shift = 0
    ds = e.label_events(gen_triggers())
    assert_equal(ds['i_start'], I_START)