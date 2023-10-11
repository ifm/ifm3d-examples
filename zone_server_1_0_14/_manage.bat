cd /d %~dp0

o3r_docker_manager  ^
--IP "192.168.0.69" ^
--log_level "INFO" ^
--log_dir "~/o3r_logs/" ^
--transfers "./src>~/share/src,./configs>~/share/configs" ^
--set_vpu_name "zone_server_vpu_000" ^
--reset_docker "yes" ^
--setup_docker_compose "./docker-compose.yml,./docker_python_deps.tar,home/oem/share,oemshare" ^
--enable_autostart "zone_server" ^
--disable_autostart "" ^
--log_caching "/home/oem/share/logs>~/o3r_logs/From_VPUs" ^
--initialize "docker-compose.yml" ^
--attach_to "zone_server"
