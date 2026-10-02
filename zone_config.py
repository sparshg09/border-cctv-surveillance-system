import json
import os


CONFIG_FILE = "camera_zones.json"


# =========================================================
# LOAD ALL CONFIGURATION
# =========================================================

def load_all_configs():

    if not os.path.exists(
        CONFIG_FILE
    ):
        return {}

    try:

        with open(
            CONFIG_FILE,
            "r"
        ) as file:

            return json.load(
                file
            )

    except Exception:

        return {}


# =========================================================
# SAVE ALL CONFIGURATION
# =========================================================

def save_all_configs(
    configs
):

    with open(
        CONFIG_FILE,
        "w"
    ) as file:

        json.dump(
            configs,
            file,
            indent=4
        )


# =========================================================
# SAVE CAMERA CONFIGURATION
# =========================================================

def save_camera_config(
    camera_id,
    fence_points,
    restricted_polygon,
    warning_polygon=None
):

    configs = (
        load_all_configs()
    )


    configs[
        camera_id
    ] = {

        "fence":
            fence_points,

        "restricted_polygon":
            restricted_polygon,

        "warning_polygon":
            (
                warning_polygon
                if warning_polygon
                is not None
                else []
            )
    }


    save_all_configs(
        configs
    )


# =========================================================
# LOAD CAMERA CONFIGURATION
# =========================================================

def load_camera_config(
    camera_id
):

    configs = (
        load_all_configs()
    )


    return configs.get(
        camera_id,
        {
            "fence": [],
            "restricted_polygon": [],
            "warning_polygon": []
        }
    )


# =========================================================
# DELETE CAMERA CONFIGURATION
# =========================================================

def delete_camera_config(
    camera_id
):

    configs = (
        load_all_configs()
    )


    if camera_id in configs:

        del configs[
            camera_id
        ]

        save_all_configs(
            configs
        )

        return True


    return False