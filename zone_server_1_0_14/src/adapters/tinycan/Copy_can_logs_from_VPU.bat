setlocal
cd /d %~dp0
cd ..
cd ..
cd ..
set /p ip=<"configs/which_ip"

call "deploy\a._Remove_known_host.bat"

set /p "vpuname=Enter name of VPU: "

set mm = %date:~4,2%
set dd = %date:~7,2%
set yyyy = %date:~10,4%
set Timestamp=%date:~4,2%.%date:~7,2%.%date:~10,4%_%time:~0,2%.%time:~3,2%.%time:~6,2%

mkdir "./logs/"
mkdir "./logs/can/"
mkdir "./logs/can/%vpuname%"
mkdir "./logs/can/%vpuname%/%Timestamp%"

scp -i ~/.ssh/o3r.pkey -r oem@%ip%:/home/oem/can_logs "./logs/can/%vpuname%/%Timestamp%"

REM: logs copied to: ./logs/%vpuname%/%Timestamp%
pause