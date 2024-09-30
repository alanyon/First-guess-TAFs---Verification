from datetime import datetime as dt
from datetime import timedelta
from data_retrieval import RetrieveObservations
from checking import CheckTafThread

NUM_TO_DIR = dict(zip(range(0, 370, 10),
                      list('NNNNNEEEEEEEEESSSSSSSSSWWWWWWWWWNNNNN')))

def main():

    metar_dirs = {'EGLL': {'N': 0, 'E': 0, 'S': 0, 'W': 0, 'VRB': 0}}

    GetObs = RetrieveObservations
    is_tafs = GetObs('EGLL', "T", dt(2022, 1, 1, 22), latest_only=False,
                     start_time=dt(2022, 1, 1, 22),
                     end_time=dt(2022, 1, 2, 10)).operation()

    fg_start = dt(2022, 1, 2, 4)
    fg_end = dt(2022, 1, 2, 10)

    for is_taf in is_tafs:

        # Get relevant METARs and SPECIs
        metars, metar_dirs = get_metars('EGLL', fg_start, fg_end, metar_dirs)

        (is_wind_ver, is_vis_ver, is_wx_ver,
         is_cld_ver, is_all_ver) = CheckTafThread('EGLL', fg_start, fg_end,
                                                  is_taf, metars).run()


def get_metars(icao, s_time, e_time, dirs):
    """
    Retireves METARs and SPECIs between two times for an ICAO code.
    """
    # Get METARs and SPECIs
    GetObs = RetrieveObservations
    metars = GetObs(icao, "M", s_time, latest_only=False, start_time=s_time,
                    end_time=e_time).operation()
    specis = GetObs(icao, "S", s_time, latest_only=False, start_time=s_time,
                    end_time=e_time).operation()

    # Collect METARs and SPECIs into single list
    metars += specis

    # Remove METARs and SPECIs recorded as 'NoRecord'
    metars = [metar for metar in metars if metar != "NoRecord"]

    # Remove duplicates (e.g. for METARs with trends)
    new_metars = []
    for ind, metar in enumerate(metars):
        if ind == 0 or metar[1] == current_metar[1]:
            current_metar = metar
        else:
            new_metars.append(current_metar)
            current_metar = metar
        if ind == len(metars) - 1:
            new_metars.append(current_metar)

    # Remove AUTO term from METARs and SPECIs as it has no value
    new_metars = [[ele for ele in metar if ele != 'AUTO']
                  for metar in new_metars]

    # Sort list so SPECIs in time order with METARs
    new_metars.sort(key=lambda x: x[1])

    # Get wind direction from METAR
    for metar in new_metars:
        w_dir = metar[2][:3]
        if w_dir.isnumeric() and int(w_dir) in NUM_TO_DIR:
            dir_lab = NUM_TO_DIR[int(w_dir)]
        elif w_dir == 'VRB':
            dir_lab = 'VRB'
        else:
            print('Problem with direction', metar)
            continue

        # Update direction count dictionary
        dirs[icao][dir_lab] += 1

    return new_metars, dirs


if __name__ == "__main__":
    main()
