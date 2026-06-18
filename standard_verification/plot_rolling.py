import os
import pandas as pd
import numpy as np
import matplotlib
from matplotlib import colors
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

DATA_DIR = os.environ['DATA_DIR']
PLOT_DIR = os.environ['PLOT_DIR']
INFO_FILE = os.environ['INFO_FILE']
SCORES = {'gerrity': 'Gerrity Skill Scores', 'peirce_0': 'Peirce Skill Scores', 
          'peirce_1': 'Peirce Skill Scores', 'peirce_2': 'Peirce Skill Scores', 
          'peirce_3': 'Peirce Skill Scores', 'peirce_4': 'Peirce Skill Scores', 
          'peirce_5': 'Peirce Skill Scores'}
PARAMS = {'vis': 'Visibility', 'clb': 'Cloud Base'}
TAF_CATS = {'vis': {'0': '<=300m', '1': '300-750m', '2': '800-1400m',
                    '3': '1500-4900m', '4': '5000-9000m', '5': '>=10000m'},
            'clb': {'0': '<=100ft', '1': '200-400ft', '2': '500-900ft',
                    '3': '1000-1400ft', '4': '>=1500ft'}}

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)

def main():

    # Load in airport info, mapping icaos to airport names
    airport_info = pd.read_csv(INFO_FILE, header=0)
    icao_dict = pd.Series(airport_info.airport_name.values,
                          index=airport_info.icao).to_dict()

    score_line_plots(icao_dict)

    confusion_plots()


def confusion_plots():
    
    # Loop through csv files in DATA_DIR/cts
    for file in os.listdir(f'{DATA_DIR}/cts'):

        # Load contingency table values into pandas dataframe
        ct_df = pd.read_csv(os.path.join(f'{DATA_DIR}/cts', file), index_col=0)

        # Get ICAO, parameter and TAF type from filename
        icao, param = file.split('_')[0], file.split('_')[2]
        taf_type = file[12: -4]

        # Create labels
        cats = ct_df.shape[0]
        fc_labels = [TAF_CATS[param][str(i)] for i in range(cats)]
        ob_labels = [TAF_CATS[param][str(i)] for i in range(cats)]

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 9))

        # Plot heatmap
        sns.heatmap(ct_df, annot=True, fmt='g', cmap='Blues', cbar=False, 
                    ax=ax, xticklabels=ob_labels, yticklabels=fc_labels)

        # Labels and title
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        ax.set_xlabel('Observed Category', fontsize=25, weight='bold')
        ax.set_ylabel('Forecast Category', fontsize=25, weight='bold')

        # Save figure
        plt.tight_layout()
        fig.savefig(f'{PLOT_DIR}/{param}_{icao}_{taf_type}_ct_heatmap.png')
        plt.close()


def score_line_plots(icao_dict):

    # Build colour palette
    blues6 = sample_shades('Blues', 6, low=0.30, high=0.95)
    reds6  = sample_shades('Reds',  6, low=0.30, high=0.95)
    green1 = ['#2ca02c']
    palette_13 = blues6 + reds6 + green1

    # Loop through csv files in DATA_DIR/stats
    for file in os.listdir(f'{DATA_DIR}/stats'):

        # Get ICAO from filename
        icao = file.split('_')[0]

        # Load file into pandas dataframe
        vdf = pd.read_csv(os.path.join(f'{DATA_DIR}/stats', file))

        # Loop through parameters
        for param in PARAMS:

            # Filter dataframe for parameter
            param_df = vdf[['Date'] + [col for col in vdf.columns 
                                       if param in col]]

            # Loop through scores and plot each one
            for score_name in SCORES:
                
                # Default plot title
                ttl = f'{icao_dict[icao]} {PARAMS[param]} {SCORES[score_name]}'

                # Filter dataframe for score
                if 'peirce' in score_name:

                    # Only 5 categories for cloud base
                    if param == 'clb' and score_name == 'peirce_5':
                        continue

                    # Filter dataframe for score
                    score, cat = score_name.split('_')
                    score_df = param_df[['Date'] + [col for col in 
                                                    param_df.columns 
                                                    if score in col]].copy()
                    score_df = score_df[['Date'] + 
                                        [col for col in score_df.columns 
                                         if col.endswith(cat)]]
                    ttl += f' (Category: {TAF_CATS[param][cat]})'
                else:
                    score = score_name
                    score_df = param_df[['Date'] + [col for col in 
                                                    param_df.columns 
                                                    if score in col]].copy()
                    
                # Convert dates
                score_df['Date'] = pd.to_datetime(score_df['Date'], 
                                                  format='%Y%m%d')
                
                # Give nice column names for plotting
                score_df.columns = name_cols(score_df.columns)
                
                # Melt dataframe for plotting
                score_df = score_df.melt(id_vars='Date',
                                         var_name='TAF Type',
                                         value_name='Score')

                # Create line plot
                fig, ax = plt.subplots(figsize=(16, 8))
                sns.lineplot(data=score_df, x='Date', y='Score', 
                             hue='TAF Type', palette=palette_13, ax=ax)
                
                # Format axes, title, legend, etc
                ax.legend(loc='upper left', bbox_to_anchor=(1.03, 1), 
                          fontsize=14)
                ax.set_xlabel('Date', fontsize=22, weight='bold')
                ax.set_ylabel('Score', fontsize=22, weight='bold')
                ax.tick_params(axis='x', labelsize=15)
                ax.tick_params(axis='y', labelsize=15)
                ax.set_title(ttl, fontsize=24, weight='bold')
                dates = score_df['Date'].sort_values().unique()
                idx = np.linspace(0, len(dates) - 1, 6, dtype=int)
                ax.set_xticks(dates[idx])
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

                # Save figure
                plt.tight_layout()
                plot_file = os.path.join(PLOT_DIR, f'{icao}_{param}_{score_name}.png')
                plt.savefig(plot_file)
                plt.close(fig)


def name_cols(columns):

    # Loop through columns and rename them to be more readable
    new_cols = []
    for col in columns:

        # Keep date column as is
        if col == 'Date':
            new_cols.append(col)
        
        # Rename other columns
        else:
            if 'opt_no_obs' in col:
                if 'ml' in col:
                    new_cols.append('Optimistic Auto TAFs\n(no obs, no ML)')
                else:
                    new_cols.append('Optimistic Auto TAFs\n(no obs, with ML)')
            elif 'opt_obs_update_1' in col:
                if 'ml' in col:
                    new_cols.append('Optimistic Auto TAFs\n(obs update 1,'
                                    ' no ML)')
                else:
                    new_cols.append('Optimistic Auto TAFs\n(obs update 1,'
                                    ' with ML)')
            elif 'opt_obs_update_2' in col:
                if 'ml' in col:
                    new_cols.append('Optimistic Auto TAFs\n(obs update 2,'
                                    ' no ML)')
                else:
                    new_cols.append('Optimistic Auto TAFs\n(obs update 2,'
                                    ' with ML)')
            elif 'pes_no_obs' in col:
                if 'ml' in col:
                    new_cols.append('Pessimistic Auto TAFs\n(no obs, no ML)')
                else:
                    new_cols.append('Pessimistic Auto TAFs\n(no obs, with ML)')
            elif 'pes_obs_update_1' in col:
                if 'ml' in col:
                    new_cols.append('Pessimistic Auto TAFs\n(obs update 1,'
                                    ' no ML)')
                else:
                    new_cols.append('Pessimistic Auto TAFs\n(obs update 1,'
                                    ' with ML)')
            elif 'pes_obs_update_2' in col:
                if 'ml' in col:
                    new_cols.append('Pessimistic Auto TAFs\n(obs update 2,'
                                    ' no ML)')
                else:
                    new_cols.append('Pessimistic Auto TAFs\n(obs update 2,'
                                    ' with ML)')
            elif 'manual' in col:
                new_cols.append('Manual TAFs')
            else:
                print(f'Column {col} not recognised')

    return new_cols


def sample_shades(cmap_name, n, low=0.30, high=0.95):
    """
    Sample 'n' visually distinct hex colors from a sequential colormap,
    avoiding extremes that are too dark/light.
    """
    cmap = matplotlib.colormaps[cmap_name]
    vals = np.linspace(low, high, n)
    return [colors.to_hex(cmap(v)) for v in vals]

        
if __name__ == "__main__":
    main()