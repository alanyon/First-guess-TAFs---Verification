
import os
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
from copy import deepcopy

import pandas as pd

# Define constants
DATADIR = os.environ['DATA_DIR']
TAF_TYPES = {'auto': 'Auto TAFs (no ML)', 'auto_ml': 'Auto TAFs (with ML)', 
             'auto_ml_up_1': 'Auto TAFs (with ML) - Obs Update 1',
             'auto_ml_up_2': 'Auto TAFs (with ML) - Obs Update 2',
             'man': 'Manual TAFs'}
BUST_TYPES = {'vis': 'Visibility Busts', 'cld': 'Cloud Busts', 
              'wind': 'Wind Busts', 'wx': 'Weather Busts', 'all': 'All Busts'}
TAF_INFO_CSV = ('/home/users/andre.lanyon/first_guess_tafs/'
                'First-guess-TAFs---Verification/standard_verification/'
                'taf_info.csv')

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)


def main():

    # Load in airport info, mapping icaos to airport names
    airport_info = pd.read_csv(TAF_INFO_CSV, header=0)
    icao_dict = pd.Series(airport_info.airport_name.values,
                          index=airport_info.icao).to_dict()

    # To collect overall stats for each icao
    icao_stats = {}

    # Loop through files in the data directory
    for filename in os.listdir(DATADIR):

        # Ignore plots directory
        if 'plots' in filename:
            continue

        # Unpickle the file
        with open(os.path.join(DATADIR, filename), 'rb') as f:
            data = pickle.load(f)

        # Extract the stats from the data dictionary
        all_stats = data['all_stats']

        # Add the stats to the overall icao stats dictionary
        for icao, stats in all_stats.items():
            if icao in icao_stats:
                for key, val in stats.items():
                    icao_stats[icao][key] += val
            else:
                icao_stats[icao] = deepcopy(stats)

    # Create a DataFrame from the icao stats
    big_stats = {'Airport': [], 'TAF Type': [], 'Bust Type': [], 
                 'Number of Busts': []}
    for icao, stats in icao_stats.items():
        for key, busts in stats.items():
            taf_type, bust_type = key.split(' ')

            big_stats['Airport'].append(icao_dict[icao])
            big_stats['TAF Type'].append(TAF_TYPES[taf_type])
            big_stats['Bust Type'].append(BUST_TYPES[bust_type])
            big_stats['Number of Busts'].append(busts)

    # Convert the dictionary to a DataFrame
    stats_df = pd.DataFrame(big_stats)

    # Create bar plot
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.barplot(data=stats_df, x='Number of Busts', y='Bust Type',
                hue='TAF Type', estimator=sum, errorbar=None, ax=ax)
    
    # Add scores on top of bars
    for ind in ax.containers:
        ax.bar_label(ind, fontsize=12)

    # Format axes, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1.08, 1), fontsize=18)
    ax.set_xlabel('Number of Busts', fontsize=22, weight='bold')
    ax.set_ylabel('Bust Type', fontsize=22, weight='bold')
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{DATADIR}/plots/summary_busts.png')
    plt.close()

    # Make plots for each airport
    for icao in icao_stats.keys():

        stats_df_icao = stats_df[stats_df['Airport'] == icao_dict[icao]]

        # Create bar plot
        fig, ax = plt.subplots(figsize=(14, 8))
        sns.barplot(data=stats_df_icao, x='Number of Busts', y='Bust Type',
                    hue='TAF Type', ax=ax)
        
        # Add scores on top of bars
        for ind in ax.containers:
            ax.bar_label(ind, fontsize=12)

        # Format axes, etc
        ax.legend(loc='upper left', bbox_to_anchor=(1.08, 1), fontsize=18)
        ax.set_xlabel('Number of Busts', fontsize=22, weight='bold')
        ax.set_ylabel('Bust Type', fontsize=22, weight='bold')
        ax.tick_params(axis='x', labelsize=14)
        ax.tick_params(axis='y', labelsize=14)
        ax.set_title(f'{icao_dict[icao]} Busts', fontsize=24, weight='bold')

        # Save and close figure
        plt.tight_layout()
        fig.savefig(f'{DATADIR}/plots/{icao}_busts.png')
        plt.close()


if __name__ == "__main__":
    main()
    print('Finished')