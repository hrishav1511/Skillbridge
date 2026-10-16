# debug_settings.py
import os
from skillbridge.config import settings
from skillbridge.database.db.database import SQLALCHEMY_DATABASE_URL

print("=== ENVIRONMENT VARIABLES ===")
print(f"ENV: {os.getenv('ENV')}")
print(f"MYSQL_USER: {os.getenv('MYSQL_USER')}")
print(f"MYSQL_PASSWORD: {os.getenv('MYSQL_PASSWORD')}")
print(f"MYSQL_HOSTNAME: {os.getenv('MYSQL_HOSTNAME')}")
print(f"MYSQL_PORT: {os.getenv('MYSQL_PORT')}")
print(f"MYSQL_DB: {os.getenv('MYSQL_DB')}")

print("\n=== SETTINGS OBJECT ===")
print(f"settings.ENV: {settings.ENV}")
print(f"settings.MYSQL_USER: {settings.MYSQL_USER}")
print(f"settings.MYSQL_PASSWORD: {settings.MYSQL_PASSWORD}")
print(f"settings.MYSQL_HOSTNAME: {settings.MYSQL_HOSTNAME}")
print(f"settings.MYSQL_PORT: {settings.MYSQL_PORT}")
print(f"settings.MYSQL_DB: {settings.MYSQL_DB}")

print("\n=== DATABASE URL ===")
print(f"SQLALCHEMY_DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")
