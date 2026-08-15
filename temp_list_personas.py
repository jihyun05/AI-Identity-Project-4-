import os
for name in sorted(os.listdir('config/personas')):
    print(repr(name), os.path.exists(os.path.join('config/personas', name)))
