"""
Script to count number of TAF busts and amends and create some plots.

Functions:
    main: Main function to extract data and create plots
    amds_corrs: Get amends and corrections counts for ICAO
    count_busts: Count number of busts in TAF
    day_icao_stats: Get day stats for ICAO
    get_day_man_tafs_metars: Extract manual TAFs and METARs for day
    get_icao_metars: Returns dictionary of METARs for specified ICAO
    get_new_data: Extracts TAFs and METARs amend and bust information
    get_tafs_infos: Returns list of TAFs with month and year info
    line_plot: Creates line plot of specified stats
    pickle_data: Pickles data to specified file
    plot_amends_total: Plots total amends for each month
    plot_busts: Plots busts for each month
    plot_amends_airports: Plots amends for each airport
    unpickle_data: Unpickles data from specified file

Written by Andre Lanyon.
"""
import sys
import pickle
from copy import deepcopy
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import metdb
import pandas as pd
import seaborn as sns
from taf_monitor.checking import CheckTafThread
from taf_monitor.time_functionality import ConstructTimeObject

import configs as cf

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)
pd.set_option('display.max_columns', None)


def main(new_data):
    """
    Extracts TAFs and METARs and compares them, collecting bust
    information.

    Args:
        new_data (str): 'yes' to load from pickled files, 'no' to start
                         from scratch, 'add' to add to existing data.
    Returns:
        None
    """
    # Extracting data takes ages
    if new_data == 'yes':

        # Get dictionaries, etc, to store data, either from pickled files
        # or create new empty ones
        stats = {
            'Month': [], 'Start Hour': [], 'Airport': [], 'TAF Length': [],
            'Visibility Busts': [], 'Cloud Busts': [], 'Wind Busts': [],
            'Weather Busts': [], 'All Busts': [], 'Number of METARs': [],
            'Number of Amends': [], 'Number of Corrections': []
        }

        # Get new data and add to data holders
        get_new_data(stats)

    # Unpickle stats dictionary
    stats = unpickle_data(f'{cf.D_DIR}/stats.pkl')

    # Add to stats if required
    if new_data == 'add':
        get_new_data(stats)

    # Convert to DataFrame
    stats_df = pd.DataFrame(stats)
    stats_df['Month'] = pd.to_datetime(stats_df['Month'], format='%Y-%m')

    # Create plots
    plot_amends_total(stats_df)
    plot_amends_airports(stats_df)
    plot_busts(stats_df, 'Bust Type')
    plot_busts(stats_df, 'Bust Type', perc=True)
    plot_busts(stats_df, 'Start Hour')
    plot_busts(stats_df, 'Start Hour', perc=True)


def amds_corrs(i_m_stats, icao, man_tafs):
    """
    Gets amends and corrections counts for ICAO and adds to holders
    dictionary.

    Args:
        i_m_stats (dict): Dictionary to store month stats for ICAO
        icao (str): ICAO to get stats
        man_tafs (list): List of manual TAFs with month and year info
    Returns:
        None
    """
    # Loop through manual TAFs
    for taf_info in man_tafs:

        # Get amend and correction info
        amend = taf_info['amend']
        correction = taf_info['correction']

        # Add to amends and corrections counts
        if amend:
            i_m_stats[icao]['amds']['num_amends'] += 1
        if correction:
            i_m_stats[icao]['amds']['num_corrections'] += 1


def count_busts(taf, metars, icao, start, end):
    """
    Counts the number of busts in a TAF by comparing it to METARs.

    Args:
        taf (str): TAF to check
        metars (list): List of METARs to check TAF against
        icao (str): ICAO of TAF
        start (datetime): Start time of TAF
        end (datetime): End time of TAF
    Returns:
        busts (dict): Dictionary of busts in TAF
        cats_covered (dict): Dictionary of categories covered by TAF
    """
    # Try to find busts
    try:
        busts, cats_covered = CheckTafThread(icao, start, end, taf,
                                             metars).run()

    # If any issues, assume TAF is bad and print error out to check
    except Exception as e:
        print(f'Error: {e}')
        busts, cats_covered = None, None
        print(f'Problem with TAF: {taf}')

    return busts, cats_covered


def day_icao_stats(i_m_stats, icao, man_tafs, metars, start_hr):
    """
    Gets day stats for ICAO and adds to holders dictionary.

    Args:
        i_m_stats (dict): Dictionary to store month stats for ICAO
        icao (str): ICAO to get stats
        man_tafs (list): List of manual TAFs with month and year info
        metars (list): List of METARs
        start_hr (str): Start hour of TAF
    Returns:
        None
    """
    # Find TAF with correct timings
    for taf_info in man_tafs:

        # Get TAF and validity datetime
        taf = taf_info['taf']
        day = taf_info['day']
        month = taf_info['month']
        year = taf_info['year']

        # Get start and end times of TAF
        try:
            start, end = ConstructTimeObject(taf[2], day, month, year).TAF()
        except Exception as e:
            print(f'Error: {e}')
            print(f'Problem with TAF time: {taf}')
            continue

        # Check if TAF start hour matches required hour
        if start.strftime('%H') != start_hr:
            continue

        # Get all METARs valid for TAF period
        v_metars = [metar for vdt, metar in metars if start <= vdt <= end]

        # Count busts
        busts, _ = count_busts(taf, v_metars, icao, start, end)

        # Move on if bad TAF found
        if busts is None:
            continue

        # Update month stats
        for w_type in ['wind', 'visibility', 'cloud', 'weather', 'all']:
            i_m_stats[icao][start_hr][f'{w_type}_busts'] += len(busts[w_type])

        # Update number of METARs used
        i_m_stats[icao][start_hr]['num_metars'] += len(busts['metars_used'])

        # Only need one TAF per start hour per day
        return


def get_day_man_tafs_metars(day):
    """
    Extracts from metdb all manual TAFs for required ICAOs for specified
    day and all METARs for required ICAOs for specified day and two
    following days (to cover all valid times covered by TAFs).

    Args:
        day (datetime): Day to extract TAFs and METARs for
    Returns:
        day_tafs (dict): Dictionary of manual TAFs for required ICAOs
        day_3_metars (dict): Dictionary of METARs for required ICAOs
    """
    # Define start and end times to search for TAFs
    start_times = [(day + timedelta(days=ind)).strftime("%Y%m%d/0000")
                   for ind in range(3)]
    end_times = [(day + timedelta(days=ind)).strftime("%Y%m%d/2359")
                 for ind in range(3)]

    # Get all TAFs for day
    all_tafs = metdb.obs(cf.METDB_EMAIL, 'TAFS',
                         keywords=['PLATFORM EG',
                                   f'START TIME {start_times[0]}Z',
                                   f'END TIME {end_times[0]}Z'],
                         elements=['ICAO_ID', 'TAF_RPT_TXT', 'YR', 'MON',
                                   'DAY', 'FCST_BGN_DAY', 'AMND_NUM',
                                   'COR_NUM'])

    # Get METARs for all possible times TAFs cover (3 days)
    all_metars = [metdb.obs(cf.METDB_EMAIL, 'METARS',
                            keywords=['PLATFORM EG',
                                      f'START TIME {start_time}Z',
                                      f'END TIME {end_time}Z'],
                            elements=['ICAO_ID', 'MTR_RPT_TXT'])
                  for start_time, end_time in zip(start_times, end_times)]

    # Get SPECIs for all possible times TAFs cover
    all_specis = [metdb.obs(cf.METDB_EMAIL, 'SPECI',
                            keywords=['PLATFORM EG',
                                      f'START TIME {start_time}Z',
                                      f'END TIME {end_time}Z'],
                            elements=['ICAO_ID', 'MTR_RPT_TXT'])
                  for start_time, end_time in zip(start_times, end_times)]

    # Get TAFs/METARs for each required ICAO and store in dictionaries
    day_tafs, day_3_metars = {}, {}
    for icao in cf.REQ_ICAOS:

        # Get TAFs for ICAO
        icao_tafs = all_tafs[all_tafs['ICAO_ID'] == icao]

        # Get TAFs and validity datetimes
        tafs_infos = get_tafs_infos(icao_tafs, icao)

        # Add to TAFs dictionary
        day_tafs[str(icao, 'utf-8').strip()] = tafs_infos

        # Get METARs and SPECIs for ICAO
        icao_metars = get_icao_metars(all_metars, icao)
        icao_specis = get_icao_metars(all_specis, icao)

        # Combine SPECIs and METARs
        icao_metars.update(icao_specis)

        # Sort list so SPECIs in time order with METARs
        new_icao_metars = sorted(icao_metars.items())

        # Add to METARs dictionary
        day_3_metars[str(icao, 'utf-8').strip()] = new_icao_metars

    return day_tafs, day_3_metars


def get_icao_metars(all_metars, icao):
    """
    Returns dictionary of METARs for specified ICAO.

    Args:
        all_metars (list): List of METARs to check
        icao (str): ICAO to check METARs for
    Returns:
        icao_metars (dict): Dictionary of METARs for specified ICAO
    """
    # To add METARs to
    icao_metars = {}

    # Loop through all METARs
    for metars in all_metars:

        # Loop through all METARs for ICAO
        i_metars = metars[metars['ICAO_ID'] == icao]
        for metar in i_metars:

            # Convert METAR text to list
            metar_list = str(metar['MTR_RPT_TXT'], 'utf-8').strip().split()
            metar_comps = metar_list[8:]

            # Ignore if format wrong
            if 'EG' not in metar_comps[0]:
                continue

            # Ignore if no record or cancelled
            if 'NoRecord' in metar_comps:
                continue

            # Remove AUTO if present
            if 'AUTO' in metar_comps:
                metar_comps.remove('AUTO')

            # Get METAR validity datetime and add to dictionary
            m_dt = ' '.join(metar_list[:2])
            metar_vdt = datetime.strptime(m_dt, '%H%MZ %d/%m/%y')
            icao_metars[metar_vdt] = metar_comps

    return icao_metars


def get_new_data(stats):
    """
    Extracts TAFs and METARs and compares them, collecting bust and
    amend information.

    Args:
        holders (dict): Dictionaries to store data
        load_data (str): 'yes' to load from pickled files, 'no' to start
                         from scratch.
    Returns:
        None
    """
    # Start with zeroed month stats template
    month_stats = {'visibility_busts': 0, 'cloud_busts': 0, 'wind_busts': 0,
                   'weather_busts': 0, 'all_busts': 0, 'num_metars': 0,
                   'num_amends': 0, 'num_corrections': 0}
    
    # Need the above template for each ICAO and start hour (including a
    # non start hour that will hold amends and corrections counts)
    i_m_stats = {
        icao: {start_hr: deepcopy(month_stats)
               for start_hr in ['00', '03', '06', '09',
                                '12', '15', '18', '21', 'amds']}
        for icao in cf.REQ_ICAO_STRS
    }

    # Define current month for tracking when month changes
    current_month = cf.DAYS[0].strftime('%Y-%m')

    # Loop though all days in period
    for day in cf.DAYS:

        # Print for info of progress
        print(day)

        # Month of day in loop
        month = day.strftime('%Y-%m')

        # If month has changed, save stats so far and reset month stats
        if month != current_month:
            for icao, airport in cf.REQ_ICAO_STRS.items():
                for start_hr in ['00', '03', '06', '09',
                                 '12', '15', '18', '21', 'amds']:
                    imh_stats = i_m_stats[icao][start_hr]
                    stats['Airport'].append(airport)
                    stats['TAF Length'].append(cf.TAF_LENS[icao])
                    stats['Month'].append(current_month)
                    stats['Start Hour'].append(start_hr)
                    stats['Visibility Busts'].append(
                        imh_stats['visibility_busts']
                    )
                    stats['Cloud Busts'].append(imh_stats['cloud_busts'])
                    stats['Wind Busts'].append(imh_stats['wind_busts'])
                    stats['Weather Busts'].append(imh_stats['weather_busts'])
                    stats['All Busts'].append(imh_stats['all_busts'])
                    stats['Number of METARs'].append(imh_stats['num_metars'])
                    stats['Number of Amends'].append(imh_stats['num_amends'])
                    stats['Number of Corrections'].append(
                        imh_stats['num_corrections']
                    )
            current_month = month
            i_m_stats = {
                icao: {start_hr: deepcopy(month_stats)
                    for start_hr in ['00', '03', '06', '09',
                                     '12', '15', '18', '21', 'amds']}
                for icao in cf.REQ_ICAO_STRS
            }

            # Pickle stats so far
            pickle_data(stats, f'{cf.D_DIR}/stats.pkl')

        # Get all TAFs and METARs for day (3 days for METARs to cover
        # TAF periods)
        try:
            man_tafs, metars = get_day_man_tafs_metars(day)
        except:
            print(f'problem retrieving for day: {day}')
            continue

        # Loop through required ICAOs
        for icao in cf.REQ_ICAO_STRS:

            # Get amends and corrections counts
            amds_corrs(i_m_stats, icao, man_tafs[icao])

            # Loop through possible TAF start hours
            for start_hr in ['00', '03', '06', '09', '12', '15', '18', '21']:

                # Get day stats for ICAO at start hour
                day_icao_stats(i_m_stats, icao, man_tafs[icao], metars[icao],
                               start_hr)


def get_tafs_infos(tafs, icao):
    """
    Returns list of TAFs with month and year info.

    Args:
        tafs (DataFrame): DataFrame of TAFs to extract info from
        icao (str): ICAO to extract TAFs for
    Returns:
        tafs_infos (list): List of TAFs with month and year info
    """
    tafs_infos = []
    for taf in tafs:

        # Get TAF elements
        taf_list = str(taf['TAF_RPT_TXT'], 'utf-8').strip().split()
        taf_elmts = taf_list[taf_list.index(str(icao, 'utf-8').strip()):]

        # Get issue day of TAF
        issue_day = datetime(year=taf['YR'], month=taf['MON'],
                             day=taf['DAY'])

        # Get validity day of TAF (carefully with month changeovers)
        if taf['FCST_BGN_DAY'] < taf['DAY']:
            v_day = issue_day + timedelta(days=1)
        else:
            v_day = issue_day

        # Define month and year of TAF start and add to list
        taf_info = {'taf': taf_elmts, 'day': taf['FCST_BGN_DAY'],
                    'month': v_day.month, 'year': v_day.year,
                    'amend': bool(taf['AMND_NUM']),
                    'correction': bool(taf['COR_NUM'])}
        tafs_infos.append(taf_info)

    return tafs_infos


def line_plot(stats, y_col, hue, img_fname, y_label, title, hue_order=None,
              figsize=(14, 6), ncol=1):
    """
    Creates line plot of specified stats.

    Args:
        stats (DataFrame): DataFrame of stats to plot
        y_col (str): Column to plot on y-axis
        hue (str): Column to use for hue
        img_fname (str): Filename to save image as
        y_label (str): Label for y-axis
        title (str): Title for plot
        hue_order (list): Order of hue entries
        figsize (tuple): Figure size
        ncol (int): Number of columns in legend
    Returns:
        None
    """
    # Create line plot
    fig, ax = plt.subplots(figsize=figsize)
    sns.lineplot(data=stats, x='Month', y=y_col,
                 hue=hue, ax=ax, marker='o', hue_order=hue_order)

    # Format axes, title, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), title=hue, ncol=ncol,
              title_fontproperties={'weight': 'bold'})
    ax.set_xlabel('Month', weight='bold')
    ax.set_ylabel(y_label, weight='bold')
    ax.set_title(title, weight='bold')

    # Reduce xtick labels to once a year
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # Save and close figure
    img_fname = f'{cf.D_DIR}/plots/{img_fname}.png'
    plt.tight_layout()
    fig.savefig(img_fname)
    plt.close()


def pickle_data(data, fname):
    """
    Pickles data to specified file.

    Args:
        data: Data to pickle
        fname (str): Filename to pickle data to
    Returns:
        None
    """
    file_object = open(fname, 'wb')
    pickle.dump(data, file_object)
    file_object.close()


def plot_amends_total(stats_df):
    """
    Plots total amends for each month.

    Args:
        stats_df (DataFrame): DataFrame of stats
    Returns:
        None
    """
    # Only need 'amd' start hour for amends stats
    stats_df = stats_df[stats_df['Start Hour'] == 'amds']

    # Get totals for each month
    total_stats = stats_df.groupby(['Month', 'TAF Length'],
                                   as_index=False).sum()

    # Create line plot
    line_plot(total_stats, 'Number of Amends', 'TAF Length',
              'total_amends', 'Number of Amends', 'Total Monthly Amends')

    # Calculate 12 month rolling mean
    total_stats = rolling_means(total_stats, 12, 'Number of Amends',
                                'TAF Length')

    # Create line plot of rolling mean
    line_plot(total_stats, 'Rolling 12 Month Mean', 'TAF Length',
              'total_amends_rolling', 'Number of Amends',
              '12 Month Rolling Mean of Amends')


def plot_busts(stats_df, hue, perc=False):
    """
    Plots total busts for each month.

    Args:
        stats_df (DataFrame): DataFrame of stats
        perc (bool): Whether to plot percentages or raw numbers
    Returns:
        None
    """
    # Remove 'amd' start hour entries
    stats_df = stats_df[stats_df['Start Hour'] != 'amds']

    # Get totals for each month
    if hue == 'Bust Type':
        total_stats = stats_df.groupby(['Month'], as_index=False).sum()
    else:
        total_stats = stats_df.groupby(['Month', hue], as_index=False).sum()

    # Define order of columns for legends
    if hue == 'Start Hour':
        order = ['00', '03', '06', '09', '12', '15', '18', '21']
        val_cols = ['All Busts']
    else:
        order = ['All Busts', 'Visibility Busts', 'Cloud Busts', 'Wind Busts',
                 'Weather Busts']
        val_cols = order

    # Convert to percentage if required, and define a few other things
    hue_lower = hue.lower().replace(' ', '_')
    if perc:

        # Calculate percentages
        for col in val_cols:
            total_stats[col] = (
                total_stats[col] /
                total_stats['Number of METARs'] * 100
            )

        # Define labels and titles
        img_name = f'total_busts_perc_{hue_lower}'
        y_label = 'Percentage of Busts'
        title = f'Monthly Percentage of TAF Busts by {hue}'
        title_rolling = (f'12 Month Rolling Mean of Percentage of Busts by '
                         f'{hue}')

    else:

        # Define labels and titles
        img_name = f'total_busts_{hue_lower}'
        y_label = 'Number of Busts'
        title = f'Monthly Number of TAF Busts by {hue}'
        title_rolling = f'12 Month Rolling Mean of Number of Busts by {hue}'

    # Melt DataFrame for plotting
    if hue == 'Bust Type':
        total_stats = total_stats.melt(id_vars=['Month'], value_vars=order,
                                       var_name=hue,
                                       value_name='Number of Busts')
        y_col = 'Number of Busts'
    else:
        y_col = 'All Busts'

    # Create line plot
    line_plot(total_stats, y_col, hue, img_name, y_label, title,
              hue_order=order)

    # Calculate 12 month rolling mean
    total_stats = rolling_means(total_stats, 12, y_col, hue)

    # Create line plot of rolling mean
    line_plot(total_stats, 'Rolling 12 Month Mean', hue,
              f'{img_name}_rolling', y_label, title_rolling,
              hue_order=order)


def plot_amends_airports(stats_df):
    """
    Plots amends per airport for each TAF length.

    Args:
        stats_df (DataFrame): DataFrame of stats
    Returns:
        None
    """
    # Only need 'amd' start hour for amends stats
    stats_df = stats_df[stats_df['Start Hour'] == 'amds']

    for taf_len in cf.TAF_LENS.values():

        # Get totals for each month
        total_stats = stats_df[stats_df['TAF Length'] == taf_len]
        total_stats = total_stats.groupby(
            ['Month', 'Airport'], as_index=False
        ).sum()

        # Define figsize and ncols
        if taf_len == 9:
            figsize=(16, 6)
            ncol=2
        else:
            figsize=(14, 6)
            ncol=1

        # Create line plot
        line_plot(total_stats, 'Number of Amends', 'Airport',
                  f'airports_amends_{taf_len}hr', 'Number of Amends',
                  f'Monthly Amends per Airport ({taf_len} Hour TAFs)',
                  figsize=figsize, ncol=ncol)

        # Calculate 12 month rolling means
        total_stats = rolling_means(total_stats, 12, 'Number of Amends',
                                    'Airport')

        # Create line plot of rolling mean
        line_plot(total_stats, 'Rolling 12 Month Mean', 'Airport',
                  f'airports_amends_{taf_len}hr_rolling', 'Number of Amends',
                  f'12 Month Rolling Mean of Amends per Airport ({taf_len} Hour TAFs)',
                  figsize=figsize, ncol=ncol)


def rolling_means(stats, period, value_col, piv_col):
    """
    Calculates rolling means for specified period.

    Args:
        stats (DataFrame): DataFrame of stats to calculate rolling means
        period (int): Period of rolling mean
        value_col (str): Column to calculate rolling mean for
        piv_col (str): Column to pivot on
    Returns:
        stats (DataFrame): DataFrame with rolling means added
    """
    # Pivot to wide format: index=Month, columns=TAF Length
    wide = (stats.assign(Month=pd.to_datetime(stats['Month']))
            .pivot(index='Month', columns=piv_col,
                   values=value_col)
            .sort_index())

    # Period-row rolling mean (strict monthly cadence)
    wide_roll = wide.rolling(window=period, min_periods=period).mean()

    # Return to long format and merge back
    roll_long = wide_roll.stack().rename('mean_12m').reset_index()
    out = stats.merge(roll_long, on=['Month', piv_col], how='left')

    stats = out.rename(columns={'mean_12m': 'Rolling 12 Month Mean'})

    # Remove months with less than 12 months of data
    stats = stats.dropna(subset=['Rolling 12 Month Mean'])

    return stats


def unpickle_data(fname):
    """
    Unpickles data from specified file.

    Args:
        fname (str): Filename to unpickle data from
    Returns:
        data: Unpickled data
    """
    with open(fname, 'rb') as file_object:
        unpickle = pickle.Unpickler(file_object)
        data = unpickle.load()

    return data


if __name__ == "__main__":

    # Print time
    time_1 = datetime.now()
    print('Started', time_1)

    # Get user defined indication for whether new data is needed
    new_data = sys.argv[1]

    # Run main function
    main(new_data)

    # Print time
    time_2 = datetime.now()
    print('Finished', time_2)

    # Print time taken
    print('Time taken (seconds):', (time_2 - time_1).total_seconds())
