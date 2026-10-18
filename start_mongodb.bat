@echo off
echo Starting MongoDB Database Server...
"%~dp0mongodb\bin\mongod.exe" --dbpath "%~dp0mongodb\data" --bind_ip 127.0.0.1 --port 27017
pause
