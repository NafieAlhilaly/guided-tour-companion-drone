# Publish new group location
new_location="18.375843,42.3782481, 0"
mosquitto_pub -t "flollow/target_location" -m "18.373417, 42.3781843,10"

# Publish alert for medical supply
mosquitto_pub -t "supplies/medical" -m "med_alert"