# !/bin/bash

# Copy and overwrite the world file in root "forest.sdf" to the PX4 directory
cp ./forest.sdf ./PX4-Autopilot/Tools/simulation/gz/worlds/forest.sdf
if [ $? -ne 0 ]; then
    echo "Failed to copy forest.sdf to PX4 directory."
    exit 1
fi
echo "Copied forest.sdf to PX4 directory."