"""
Module to produce plots and spreadsheets for bust TAF verification.

Functions:
    create_dirs: Creates directories if needed.
    mets_all: Writes METAR to spreadsheet.
    mets_wind: Writes METAR to spreadsheet.
    plot_dirs: Plots bar charts showing bust information for each TAF.
    plot_param: Plots parameter-specific bar chart.
    plot_summary: Plots summary bar chart showing bust information.
    taf_str: Converts TAF in list format to and easily readable string.
    write_to_excel: Writes verification info to Excel file.
    write_stats: Writes stats to spreadsheet, returning row number.

Written by Andre Lanyon
"""
import os

import matplotlib.pyplot as plt
import seaborn as sns
import xlsxwriter
import pandas as pd
import numpy as np

import configs as cf

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)


def create_dirs():
    """
    Creates directories if needed.

    Args:
        None
    Returns:
        None
    """
    # Make plots directory if needed
    if not os.path.exists(f'{cf.D_DIR}/plots'):
        os.makedirs(f'{cf.D_DIR}/plots')

    # Loop through each ICAO
    for icao in cf.REQ_ICAO_STRS:

        # Make directory if needed
        if not os.path.exists(f'{cf.D_DIR}/plots/{icao}'):
            os.makedirs(f'{cf.D_DIR}/plots/{icao}')


def mets_all(ver_lst, worksheet, workbook, m_row_num, col):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.

    Args:
        ver_lst (list): List of busts
        worksheet (obj): Worksheet object
        workbook (obj): Workbook object
        m_row_num (int): Row number in spreadsheet
        col (int): Column number in spreadsheet
    Returns:
        new_lines (int): Number of new lines added to spreadsheet
    """
    # For keeping track of rows in spreadsheet
    new_lines = 0

    # Loop through each bust in list
    for bust in ver_lst:

        # Unpack list
        bust_types, metar, _,  = bust

        # Join ypes of bust together
        msg = ' and '.join(bust_types)

        # Colour METAR based on bust type
        if 'wind' in msg:
            if msg == 'wind':
                colour = 'red'
            elif 'visibility'in msg:
                colour = 'orange'
            elif 'weather' in msg:
                colour = 'gold'
            elif 'cloud' in msg:
                colour = 'green'
        elif 'visibility' in msg:
            if msg == 'visibility':
                colour = 'lime'
            elif 'weather' in msg:
                colour = 'cyan'
            elif 'cloud' in msg:
                colour = 'blue'
        elif 'weather' in msg:
            if msg == 'weather':
                colour = 'blueviolet'
            elif 'cloud' in msg:
                colour = 'magenta'
        elif 'cloud' in msg:
            colour = 'purple'

        # Create format
        b_form = workbook.add_format({'bold': True, 'font_color': colour})

        # Convert METAR to string and add bust type message
        metar_str = msg + ' - ' + ' '.join(metar)

        # Add METAR to spreadsheet
        worksheet.write(m_row_num, col, metar_str, b_form)

        # Add to row number and new_lines vrb
        m_row_num += 1
        new_lines += 1

    return new_lines


def mets_wind(ver_lst, worksheet, workbook, m_row_num, col):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.

    Args:
        ver_lst (list): List of busts
        worksheet (obj): Worksheet object
        workbook (obj): Workbook object
        m_row_num (int): Row number in spreadsheet
        col (int): Column number in spreadsheet
    Returns:
        new_lines (int): Number of new lines added to spreadsheet
    """
    # For keeping track of rows in spreadsheet
    new_lines = 0

    # Loop through each bust in list
    for bust in ver_lst:

        # Unpack list
        bust_types, metar, _ = bust

        # Colour METAR based on bust type
        if bust_types['mean increase'] or bust_types['gust increase']:
            if bust_types['dir']:
                colour = 'purple'
                msg = 'Increase/dir - '
            else:
                colour = 'red'
                msg = 'Increase - '
        elif bust_types['mean decrease']:
            if bust_types['dir']:
                colour = 'green'
                msg = 'Decrease/dir - '
            else:
                colour = 'gold'
                msg = 'Decrease - '
        elif bust_types['dir']:
            colour = 'blue'
            msg = 'Dir - '
        else:
            colour = None
            msg = 'Unknown - '

        # Create format
        if colour:
            fmt = workbook.add_format({'bold': True, 'font_color': colour})
        else:
            fmt = workbook.add_format({'bold': True})

        # Convert METAR to string and add bust type message
        metar_str = msg + ' '.join(metar)

        # Add METAR to spreadsheet
        worksheet.write(m_row_num, col, metar_str, fmt)

        # Add to row number and new_lines vrb
        m_row_num += 1
        new_lines += 1

    return new_lines


def plot_cats(holders):

    stats = {'TAF Type': [], 'Parameter': [], 
             'Mean No. of Categories Covered': []}
    
    # Loop through all icaos
    for icao in cf.REQ_ICAO_STRS:

        # Loop through vis and cld
        for param in ['vis', 'cld']:

            # Loop through taf types
            for t_type, t_name in cf.TAF_TYPES.items():

                # Get mean number of categories covered and add to 
                # dictionary
                cats = holders[f'{param}_cats'][icao][t_type]
                stats['TAF Type'].append(t_name)
                stats['Parameter'].append(param)
                stats['Mean No. of Categories Covered'].append(np.mean(cats))

    # Create dataframe from stats
    plot_stats = pd.DataFrame(stats)

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create box plot
    g_box = sns.boxplot(data=plot_stats, x='Parameter', 
                        y='Mean No. of Categories Covered', 
                        hue='TAF Type', ax=ax)

    # Add vertical line separating parameters
    ax.axvline(0.5, color='white', linestyle='--', alpha=0.5)

    # Formatting, etc
    ax.set_xlabel('Parameter', weight='bold')
    ax.set_ylabel('Mean No. of Categories Covered', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.setp(g_box.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/cats_covered_ml.png')
    plt.close()


def plot_dirs(holders):
    """
    Plots bar charts showing bust information for each TAF, separating busts
    by METAR wind direction.

    Args:
        holders (dict): Dictionaries of data
    Returns:
        None
    """
    # Make plots for each ICAO
    for icao in cf.REQ_ICAO_STRS:

        # Get required data
        dirs_data = {'TAF Type': [], 'Number of Busts': [], 'Direction': []}
        for t_type, t_name in cf.TAF_TYPES.items():
            d_stats = holders['dirs_stats'][f'{t_type} dirs'][icao]['dir']
            for wdir, num in d_stats.items():
                dirs_data['TAF Type'].append(t_name)
                dirs_data['Number of Busts'].append(num)
                dirs_data['Direction'].append(wdir)

        # Create bar plot
        fig, ax = plt.subplots(figsize=(10, 10))
        sns.barplot(data=dirs_data, x='Number of Busts', y='TAF Type',
                    hue='Direction')

        # Add scores on top of bars
        for ind in ax.containers:
            ax.bar_label(ind, fontsize=14)

        # Format axes, etc
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1),
                  title='Wind\nDirection')
        ax.set_xlabel('Number of Busts', weight='bold')
        ax.set_ylabel('Bust Type', weight='bold')

        # Save and close figure
        img_fname = f'{cf.D_DIR}/plots/{icao}/dir_busts_ml.png'
        plt.tight_layout()
        fig.savefig(img_fname)
        plt.close()


def plot_param(holders, param, summary_stats):
    """
    Plots parameter-specific bar chart showing bust information.

    Args:
        holders (dict): Dictionaries to store data
        param (str): Parameter to plot
        summary_stats (dict): Dictionary to store summary stats
    Returns:
        t_busts (dict): Dictionary of bust numbers
    """
    # Get stats dictionary
    stats_abs = holders[f'{param}_stats']

    # Titles, etc, for creating stats dataframes
    t_num = len(cf.TAF_TYPES)
    if param == 'wind':
        bust_types = ['Observed\nwind higher', 'Observed\nwind lower',
                      'Wind direction\nbusts', 'Total\nwind busts'] * t_num
        taf_types = sum([[p_label] * 4 for p_label in cf.TAF_TYPES.values()],
                        [])
        bust_keys = sum([[f'{t_type} increase', f'{t_type} decrease',
                          f'{t_type} dir', f'{t_type} all']
                         for t_type in cf.TAF_TYPES], [])
    elif param == 'wx':
        bust_types = ['Significant\nweather busts'] * t_num
        taf_types = cf.TAF_TYPES.values()
        bust_keys = [f'{t_type} all' for t_type in cf.TAF_TYPES]
    else:
        bust_types = [f'Observed\n{cf.W_NAMES[param]} higher',
                      f'Observed\n{cf.W_NAMES[param]} lower',
                      f'Total\n{cf.W_NAMES[param]} busts'] * t_num
        taf_types = sum([[p_label] * 3 for p_label in cf.TAF_TYPES.values()],
                        [])
        bust_keys = sum([[f'{t_type} increase', f'{t_type} decrease',
                          f'{t_type} all'] for t_type in cf.TAF_TYPES], [])

    # Add to summary_stats with number of busts to be updated in
    # following for loop
    summary_stats['Bust Type'].extend(bust_types)
    summary_stats['TAF Type'].extend(taf_types)
    total_busts = [0 for _ in bust_types]

    # Loop through all icaos
    t_busts = {}
    for icao in stats_abs:

        # Only get stats from required ICAOs
        if icao not in cf.REQ_ICAO_STRS:
            continue

        # # Only get stats from required ICAOs
        # if icao not in cf.NINE_HR_STRS:
        #     continue

        # Get stats for airport
        stats = stats_abs[icao]

        # Add to or create t_busts dictionary
        if t_busts == {}:
            for b_key in bust_keys:
                t_busts[b_key] = [stats[b_key]]
        else:
            for b_key, busts in stats.items():
                if b_key in bust_keys:
                    t_busts[b_key].append(busts)

        # Get bust numbers for icao
        icao_busts = [stats[b_key] for b_key in bust_keys]

        # Update total bust numbers
        total_busts = [x + y for x, y in zip(total_busts, icao_busts)]

        # Create dataframe from stats
        pd_stats = {'Bust Type': bust_types, 'TAF Type': taf_types,
                    'Number of Busts': icao_busts}

        # Create bar plot
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.barplot(data=pd_stats, x='Number of Busts', y='Bust Type',
                    hue='TAF Type')

        # Add scores on top of bars
        for ind in ax.containers:
            ax.bar_label(ind, fontsize=14)

        # Format axes, etc
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.set_xlabel('Number of Busts', weight='bold')
        ax.set_ylabel('Bust Type', weight='bold')

        # Save and close figure
        img_fname = f'{cf.D_DIR}/plots/{icao}/{param}_busts_ml.png'
        plt.tight_layout()
        fig.savefig(img_fname)
        plt.close()

    # Add to bust numbers in summary_stats
    summary_stats['Number of Busts'].extend(total_busts)

    return t_busts


def plot_summary(summary_stats):
    """
    Plots summary bar chart showing bust information.

    Args:
        summary_stats (dict): Dictionary of summary stats
    Returns:
        None
    """
    # Create bar plot
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.barplot(data=summary_stats, x='Number of Busts', y='Bust Type',
                hue='TAF Type')

    # Add scores on top of bars
    for ind in ax.containers:
        ax.bar_label(ind, fontsize=16)

    # Format axes, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1.1, 1), fontsize=18)
    ax.set_xlabel('Number of Busts', fontsize=22, weight='bold')
    ax.set_ylabel('Bust Type', fontsize=22, weight='bold')
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/summary_busts_ml.png')
    plt.close()


def plot_taf_lens(holders):

    stats = {'TAF Type': [], 'Mean TAF Length': [], 'Airport': []}

    # Loop through all icaos
    for icao in cf.REQ_ICAO_STRS:

        # Loop through taf types
        for t_type, t_name in cf.TAF_TYPES.items():

            # Get mean TAF length and add to dictionary
            taf_lens = holders[f'taf_lens'][icao][t_type]
            stats['TAF Type'].append(t_name)
            stats['Mean TAF Length'].append(np.mean(taf_lens))
            stats['Airport'].append(cf.REQ_ICAO_STRS[icao])

    # Create dataframe from stats
    plot_stats = pd.DataFrame(stats)

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 10))

    # Create box plot
    t_bar = sns.barplot(data=plot_stats, y='Airport', x='Mean TAF Length', 
                        hue='TAF Type', ax=ax)

    # Formatting, etc
    ax.set_xlabel('Mean TAF Length', weight='bold')
    ax.set_ylabel('Airport', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=12)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.setp(t_bar.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/taf_lengths_ml.png')
    plt.close()

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(8, 4))

    # Create box plot
    t_box = sns.boxplot(data=plot_stats, y='TAF Type', x='Mean TAF Length', 
                        ax=ax)

    # Formatting, etc
    ax.set_xlabel('Mean TAF Length', weight='bold')
    ax.set_ylabel('TAF Type', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=15)

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/taf_lengths_box_ml.png')
    plt.close()


def plot_wx(holders):
    """
    Plots bust info relating to sig wx codes.

    Args:
        holders (dict): Dictionaries to store data
    Returns:
        None
    """
    # Get stats dictionary
    stats_abs = holders[f'wx_stats']

    # Loop through all icaos
    plot_stats = {}
    for icao in stats_abs:

        # Only get stats from required ICAOs
        if icao not in cf.REQ_ICAO_STRS:
            continue

        # # Only get stats from required ICAOs
        # if icao not in cf.NINE_HR_STRS:
        #     continue

        # Get stats for airport
        stats = stats_abs[icao]

        # Separate out reasons for bust and add to dictionary
        for full_b_type, n_busts in stats.items():

            # Get TAF and bust type and 
            t_type = full_b_type[:2]
            b_type = full_b_type[3:]

            # Ignore 'all' types
            if b_type == 'all':
                continue

            # Get full TAF type name
            t_name = cf.TAF_TYPES[t_type]

            # Add to stats dictionary
            if b_type not in plot_stats:
                plot_stats[b_type] = {tnm: 0 for tnm in cf.TAF_TYPES.values()}
            plot_stats[b_type][t_name] += n_busts
            
    # Rearrange dictionary for a bar chart
    bar_stats = {'TAF Type': [], 'Bust Type': [], 'Number of Busts': []}
    for b_type, t_dict in plot_stats.items():
        for t_name, n_busts in t_dict.items():
            bar_stats['TAF Type'].append(t_name)
            bar_stats['Bust Type'].append(b_type)
            bar_stats['Number of Busts'].append(n_busts)

    # Convert to dataframe
    bar_df = pd.DataFrame(bar_stats)

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create box plot
    g_box = sns.barplot(data=bar_df, y='Bust Type', x='Number of Busts', 
                        hue='TAF Type', ax=ax)

    # Add scores on top of bars
    for ind in ax.containers:
        ax.bar_label(ind, fontsize=10)

    # Formatting, etc
    ax.set_xlabel('Bust Type', weight='bold')
    ax.set_ylabel('Number of Busts', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=10)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.setp(g_box.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/wx_busts_ml.png')
    plt.close()


def taf_str(taf_lst):
    """
    Converts TAF in list format to and easily readable string.

    Args:
        taf_lst (list): List of TAF details
    Returns:
        stringy_taf (str): TAF as a string
        num_lines (int): Number of lines in TAF
    """
    # variables to update
    new_taf = []
    num_lines = 0

    # Loop through each TAF elemant
    for ind, ele in enumerate(taf_lst):

        # Add line breaks and spaces before certain TAF terms and append
        # new strings to new_taf list
        if ele in cf.TAF_TERMS:
            if 'PROB' not in taf_lst[ind -1]:
                new_taf.append(f'\n    {ele}')
                num_lines += 1
            else:
                new_taf.append(ele)
        else:
            new_taf.append(ele)

    # Create string from list
    stringy_taf = ' '.join(new_taf)

    return stringy_taf, num_lines


def write_to_excel(holders, w_type):
    """
    Writes verification info to Excel file.

    Args:
        holders (dict): Dictionaries of data
        w_type (str): Type of weather to write to Excel file
    Returns:
        None
    """
    # Get required data
    w_stats = holders[f'{w_type}_stats']
    w_info = holders[f'{w_type}_info']

    # Open Excel workbook
    fname = f'{w_type}_vers.xlsx'
    workbook = xlsxwriter.Workbook(fname)

    # Create separate worksheet for each ICAO
    for icao in w_info:

        # Move to next iteration if no data
        if not w_info[icao]:
            continue

        # Otherwise, create worksheet
        worksheet = workbook.add_worksheet(icao)

        # Define formats for filling cells
        taf_format = workbook.add_format({'text_wrap': True})
        bold = workbook.add_format({'bold': True})
        big_bold = workbook.add_format({'bold': True, 'underline': True,
                                        'font_size': 14})

        # Variables specific to weather type
        if w_type == 'wind':
            msgs = ['Total number of wind', 'Increased wind', 'Decreased wind',
                    'Directional wind']
            keys = ['all', 'increase', 'decrease', 'dir']
        else:
            msgs = ['Total', 'Total wind', 'Total visibility',
                    'Total significant weather', 'Total cloud busts']
            keys = ['all', 'wind', 'vis', 'wx', 'cld']

        # For keeping track of rows to write to
        row_num = 0

        # Title
        t_str = w_type.capitalize()
        worksheet.write(row_num, 0,
                        f'{t_str} Busts for {cf.REQ_ICAO_STRS[icao]}',
                        big_bold)
        row_num += 2

        # Get ICAO stats
        i_stats = w_stats[icao]

        # Titles
        for ind, title in enumerate(cf.TAF_TYPES.values()):
            worksheet.write(row_num, ind * 12,
                            f'{title.replace("\n", " ")} Statistics', big_bold)

        # Write stats to spreadsheet
        for msg, key in zip(msgs, keys):
            row_num = write_stats(worksheet, bold, i_stats, msg, key, row_num)
        row_num += 2

        # Loop through all TAFs
        for item in w_info[icao]:

            # Add header for each TAF type
            for ind, t_type in enumerate(item):
                worksheet.write(row_num, ind * 12,
                                cf.TAF_TYPES[t_type].replace('\n', ' '),
                                big_bold)

            # Add to row number
            row_num += 1

            # Add TAF for each TAF type
            all_lines = []
            for ind, (t_type, (taf, _)) in enumerate(item.items()):

                # Change TAF format to add to worksheet
                t_taf, lines = taf_str(taf)
                # print('t_taf', t_taf)

                all_lines.append(lines)

                # Write TAF to spreadsheet
                worksheet.merge_range(row_num, ind * 12, row_num + lines,
                                      ind * 12 + 6, t_taf, taf_format)

            # Add to row number
            row_num += max(all_lines) + 2

            # Busts header
            for ind in range(len(item)):
                worksheet.write(row_num, ind * 12, 'TAF Busts', big_bold)

            # Add to row number
            row_num += 1

            # Add METARs for each TAF type
            all_lines = []
            for ind, (t_type, (_, ver)) in enumerate(item.items()):
                if w_type == 'wind':
                    all_lines.append(mets_wind(ver, worksheet, workbook,
                                               row_num, ind * 12))
                else:
                    all_lines.append(mets_all(ver, worksheet, workbook,
                                              row_num, ind * 12))

            # Add to row number
            row_num += max(all_lines) + 2

    # Close workbook
    workbook.close()

    # Copy Excel file to ml_plots directory
    os.system(f'mv {fname} {cf.D_DIR}/plots')


def write_stats(worksheet, fmt, stats_dict, msg, key_stat, r_num):
    """
    Writes stats to spreadsheet, returning row number.

    Args:
        worksheet (xlsxwriter.worksheet): Worksheet to write to
        fmt (xlsxwriter.format): Format to write in
        stats_dict (dict): Dictionary of stats
        msg (str): Message to write
        key_stat (str): Key to access stats
        r_num (int): Row number to write to
    Returns:
        r_num (int): Updated row number
    """
    r_num += 1
    for ind, t_type in enumerate(cf.TAF_TYPES):
        t_stat = stats_dict[f'{t_type} {key_stat}']
        t_str = f'{msg} busts: {t_stat}'
        worksheet.write(r_num, ind * 12, t_str, fmt)

    return r_num
