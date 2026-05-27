import math
import os
import random

import psycopg2

DB_URL = os.getenv(
    "POSTGRES_URL", "postgresql://up_election_app_user:app_password@localhost:5432/gorakhpur_db"
)


def scatter():
    print("Connecting to DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Base coordinate for Gorakhpur Urban
    BASE_LAT = 26.7588
    BASE_LON = 83.3697

    cur.execute("SELECT booth_id FROM booth_master;")
    booths = cur.fetchall()

    print(f"Scattering {len(booths)} booths...")

    for (booth_id,) in booths:
        # random radius up to ~5km
        r = 0.05 * math.sqrt(random.random())
        theta = random.random() * 2 * math.pi

        lat = BASE_LAT + (r * math.cos(theta))
        lon = BASE_LON + (r * math.sin(theta))

        cur.execute(
            "UPDATE booth_master SET lat = %s, lon = %s WHERE booth_id = %s;", (lat, lon, booth_id)
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Done!")


if __name__ == "__main__":
    scatter()
