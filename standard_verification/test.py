import os
import json

a = os.environ.get('PLOT_TITLES')
a_dict = json.loads(a)
for x in a_dict:
    print(x)
    print(a_dict[x])
