# app/config.py
import os
from dotenv import load_dotenv
load_dotenv()

# Common credentials
DB_HOST = "twobyrdz-database-nov-13-backup-do-user-2438392-0.h.db.ondigitalocean.com"
DB_PORT = 25060
DB_USER = "doadmin"
DB_PASSWORD = "AVNS_al6i3oenVYlmUUaxTFz"

# Separate DB names
APP_DB_NAME = "telehotwire"     # For users and metadata
OPENFIRE_DB_NAME = "defaultdb"  # For ofMessageArchive etc.
