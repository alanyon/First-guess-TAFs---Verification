import os

# Import TAF types and data directory
TAF_TYPES = os.environ['TAF_TYPES'].split()
DATA_DIR = os.environ['DATA_DIR']


def main():
    """
    Update config files with new data directory.
    """
    # Loop through TAF types
    for t_type in TAF_TYPES:

        # Ignore operational file
        if t_type == 'Manual':
            continue

        # Open config file
        with open(f'{t_type}.cfg', 'r') as t_file:
            
            # Read lines
            lines = t_file.readlines()

        # Change path in second line
        new_lines = (f'taf_connection_string = sqlite:///{DATA_DIR}/decodes'
                     f'/test_{t_type.lower()}.db\n')
        lines[1] = new_lines

        # Save new config file
        with open(f'{t_type}.cfg', 'w') as t_file:
            t_file.writelines(lines)


if __name__ == '__main__':
    main()