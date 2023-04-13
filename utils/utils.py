import os


def save_data_to_disk(data, filename, save_folder, userid):
    DATAPATH_FOLDER = os.path.join('saved_data', save_folder)
    DATAPATH_USER = os.path.join(DATAPATH_FOLDER, userid)

    if not os.path.exists(DATAPATH_FOLDER):
        os.makedirs(DATAPATH_FOLDER)

    if not os.path.exists(DATAPATH_USER):
        os.makedirs(DATAPATH_USER)

    with open(os.path.join(DATAPATH_USER, filename), 'w') as f:
        f.write(data)


def fetch_data_from_disk(filename, save_folder, userid):
    with open(os.path.join('saved_data', save_folder, userid, filename), 'r') as f:
        data = f.read()
    return data


def check_if_saved_data_exists(filename_list, save_folder, userid):
    return all(os.path.exists(os.path.join('saved_data', save_folder, userid, filename)) for filename in filename_list)


def hex_to_rgba(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'
