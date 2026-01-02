# !/bin/bash

# Check if is PXfirst instance is running, if its not, exit the script
PX4_RUNNING=$(pgrep -f px4_sitl_default)
if [ -z "$PX4_RUNNING" ]; then
    echo "PX4 instance is not running. Please start PX4 first."
    exit 1
fi


i=1
cd ./PX4-Autopilot
gnome-terminal -- bash -c "PX4_UXRCE_DDS_NS=px4_1 PX4_SYS_AUTOSTART='400${i}' PX4_SIM_MODEL=gz_x500_depth PX4_GZ_MODEL_POSE='12,23,0' ./build/px4_sitl_default/bin/px4 -i $i; exec bash"

