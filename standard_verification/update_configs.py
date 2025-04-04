import os

# Import TAF types and data directory
TAF_TYPES = os.environ['TAF_TYPES'].split()
DECODE_DIR = os.environ['DECODE_DIR']


def main():
    """
    Update config files with new data directory.
    """
    # Loop through TAF types
    for t_type in TAF_TYPES:

        # Ignore operational file
        if t_type == 'Manual':
            continue

        # Define lines to write to config file
        lines = ['[defaults]\n',
                 f'taf_connection_string = sqlite:///{DECODE_DIR}/{t_type}.db\n',
                 'metar_connection_string = oracle://:@verifyop\n',
                 'table_schema = cfsb\n',
                 'taf_table = taf_decoded_data\n',
                 'rawtaf_table = taf_data\n',
                 'metar_table = sbv_metar_decoded_data\n',
                 'extract_lookahead = 3\n',
                 'sql_debug = False\n',
                 ('vis_cats = Category.from_thresh([350, 800, 1500, 5000, '
                 '10000])\n'),
                 'clb_cats = Category.from_thresh([200, 500, 1000, 1500])\n',
                 'ft_to_m = 0.3048\n',
                 'use_autometars = True\n',
                 'use_specis = False\n',
                 'probbins = Problist([0.0, 0.3, 0.4, 0.6, 0.7, 1.0])\n',
                 ('probbins_uncertainty = Problist([0.00, 0.05, 0.10, 0.15, '
                  '0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65,'
                  ' 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00])\n'),
                  'vis_verpy_str = vis\n',
                 'clb_verpy_str = cbh|5.0\n', 
                 'metars_per_hour = 2\n']

        # Write lines to config file
        with open(f'{t_type}.cfg', 'w') as t_file:
            t_file.writelines(lines)


if __name__ == '__main__':
    main()