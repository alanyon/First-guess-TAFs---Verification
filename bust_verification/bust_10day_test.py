"""Scratch script: runs the real verify_busts pipeline (process_days +
make_plots) for the first 10 verification days, writing to scratch
pickle/output locations so production data (pickles, bust_plots) is left
untouched. This is a precursor to the full multi-year run."""
import sys

sys.path.insert(0, '/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification/bust_verification')

import configs as cf
import verify_busts as vb

NUM_TEST_DAYS = 10

test_pickle_dir = '/data/users/andre.lanyon/tafs/verification/bust_10day_test_pickles'
test_out_dir = '/data/users/andre.lanyon/tafs/verification/bust_10day_test_output'

cf.PICKLE_DIR = test_pickle_dir
cf.D_DIR = test_out_dir
cf.OUT_DIR = test_out_dir

holders = vb.make_empty_holders()
vb.process_days(holders, cf.DAYS[:NUM_TEST_DAYS], test_pickle_dir)

print('Days processed:', NUM_TEST_DAYS)
print('METARs used (sum):', sum(holders['metars_used'].values()))

# Run the exact same plotting pipeline used in production
vb.make_plots(holders)

print('Plots written to:', f'{test_out_dir}/bust_plots')
