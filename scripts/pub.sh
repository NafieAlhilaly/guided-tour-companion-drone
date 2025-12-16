# Publish new group location
new_location="18.375843,42.3782481, 0"
mosquitto_pub -t "flollow/target_location" -m "$new_location"