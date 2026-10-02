import os
import glob
import sqlite3


DB_NAME = "alpr.db"


# =========================================================
# FILES TO DELETE
# =========================================================

RESULT_FILES = [
    "detections.csv",
    "people_detections.csv",
    "intrusion_alerts.csv",
    "security_events.csv",
    "output_detected.mp4",
    "output_detected_h264.mp4"
]


# =========================================================
# SNAPSHOT FOLDERS TO CLEAR
# =========================================================

SNAPSHOT_FOLDERS = [
    "snapshots/people",
    "snapshots/vehicles",
    "snapshots/plates",
    "snapshots/intrusions",
    "snapshots/fence",
    "snapshots/groups"
]


# =========================================================
# DELETE RESULT FILES
# =========================================================

def clear_result_files():

    for path in RESULT_FILES:

        if os.path.exists(path):

            try:
                os.remove(path)
                print(f"Deleted: {path}")

            except Exception as e:
                print(
                    f"Could not delete {path}: {e}"
                )


# =========================================================
# CLEAR SNAPSHOTS
# =========================================================

def clear_snapshots():

    for folder in SNAPSHOT_FOLDERS:

        if not os.path.exists(folder):
            continue


        files = glob.glob(
            os.path.join(
                folder,
                "*"
            )
        )


        for path in files:

            if os.path.isfile(path):

                try:
                    os.remove(path)

                except Exception as e:
                    print(
                        f"Could not delete {path}: {e}"
                    )


        print(
            f"Cleared: {folder}"
        )


# =========================================================
# CLEAR DATABASE SURVEILLANCE HISTORY
# =========================================================

def clear_database_history():

    if not os.path.exists(DB_NAME):

        print(
            "Database not found."
        )

        return


    conn = sqlite3.connect(
        DB_NAME
    )

    cursor = conn.cursor()


    # -----------------------------------------------------
    # GET EXISTING TABLES
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        """
    )


    existing_tables = {
        row[0]
        for row in cursor.fetchall()
    }


    # -----------------------------------------------------
    # DETECTIONS
    # -----------------------------------------------------

    if "detections" in existing_tables:

        cursor.execute(
            "DELETE FROM detections"
        )

        print(
            "Cleared database: detections"
        )


    # -----------------------------------------------------
    # PEOPLE
    # -----------------------------------------------------

    if "people" in existing_tables:

        cursor.execute(
            "DELETE FROM people"
        )

        print(
            "Cleared database: people"
        )


    # -----------------------------------------------------
    # PERSON DETECTIONS
    # -----------------------------------------------------

    if "person_detections" in existing_tables:

        cursor.execute(
            "DELETE FROM person_detections"
        )

        print(
            "Cleared database: person_detections"
        )


    # -----------------------------------------------------
    # INTRUSION ALERTS
    # -----------------------------------------------------

    if "intrusion_alerts" in existing_tables:

        cursor.execute(
            "DELETE FROM intrusion_alerts"
        )

        print(
            "Cleared database: intrusion_alerts"
        )


    conn.commit()

    conn.close()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print()

    print(
        "========================================"
    )

    print(
        "CLEARING OLD SURVEILLANCE RESULTS"
    )

    print(
        "========================================"
    )


    clear_result_files()

    clear_snapshots()

    clear_database_history()


    print()

    print(
        "========================================"
    )

    print(
        "OLD SURVEILLANCE RESULTS CLEARED"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Preserved:"
    )

    print(
        "✅ Vehicle blacklist"
    )

    print(
        "✅ camera_zones.json"
    )

    print(
        "✅ Saved fence configurations"
    )

    print(
        "✅ Demo videos"
    )

    print(
        "✅ Models and project code"
    )