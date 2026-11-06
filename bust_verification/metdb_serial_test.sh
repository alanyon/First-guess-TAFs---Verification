#!/bin/bash -l
#SBATCH --partition=cpu-long
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --time=02:00:00

set -eo pipefail
BASE=/home/users/andre.lanyon/first_guess_tafs/First-guess-TAFs---Verification
source "${BASE}/standard_verification/setup_constants.sh"
conda activate default_clone_may_2026
export PYTHONPATH="${PYTHONPATH}:${HOME}/python:${BASE}/taf_monitor"
cd "${BASE}/bust_verification"

python -u - <<'PY'
import sys
import traceback
from datetime import datetime
from time import perf_counter

import verify_busts as vb

original_obs = vb.metdb.obs


def timed_obs(*args, **kwargs):
    report_type = args[1]
    keywords = kwargs.get('keywords', [])
    print(f'{datetime.now().isoformat()} REQUEST {report_type} {keywords}',
          flush=True)
    started = perf_counter()
    try:
        result = original_obs(*args, **kwargs)
    except Exception as error:
        print(f'REQUEST FAILED {report_type} after '
              f'{perf_counter() - started:.1f}s: '
              f'{type(error).__name__}: {error}', flush=True)
        raise
    print(f'REQUEST OK {report_type} after '
          f'{perf_counter() - started:.1f}s; rows={len(result)}', flush=True)
    return result


vb.metdb.obs = timed_obs
dates = ['20230805', '20230820', '20230904']
failures = 0
print(f'Serial retrieval test started {datetime.now().isoformat()}; '
      f'timeout={vb.RETRIEVE_TIMEOUT}s', flush=True)
for date in dates:
    day = datetime.strptime(date, '%Y%m%d')
    started = perf_counter()
    print(f'DATE START {day.date()}', flush=True)
    try:
        tafs, metars = vb.get_day_man_tafs_metars(day)
    except Exception as error:
        failures += 1
        print(f'DATE FAILED {day.date()} after '
              f'{perf_counter() - started:.1f}s: '
              f'{type(error).__name__}: {error}', flush=True)
        print(f'DATE FAILED {day.date()}', file=sys.stderr, flush=True)
        traceback.print_exc()
    else:
        print(f'DATE OK {day.date()} after '
              f'{perf_counter() - started:.1f}s; '
              f'TAFs={sum(map(len, tafs.values()))}; '
              f'observations={sum(map(len, metars.values()))}', flush=True)

print(f'SUMMARY: {len(dates) - failures}/{len(dates)} dates succeeded; '
      f'{failures}/{len(dates)} failed', flush=True)
sys.exit(1 if failures else 0)
PY