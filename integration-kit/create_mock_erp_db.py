#!/usr/bin/env python3
"""
Seed script to initialize integration-kit/mock_erp.db with sample college students.
"""

import os
from sample_erp_connector import init_mock_erp_db, DB_PATH

if __name__ == "__main__":
    print(f"Initializing mock ERP SQLite database at: {DB_PATH}")
    init_mock_erp_db(DB_PATH)
    print("Database initialized successfully with 10 sample student records.")
