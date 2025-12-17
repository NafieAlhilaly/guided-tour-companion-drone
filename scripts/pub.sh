# Publish new group location
new_location="18.375843,42.3782481, 0"
mosquitto_pub -t "/command/follow" -m "18.373403, 42.3778063, 10"

# Publish alert for medical supply
mosquitto_pub -t "/notification/med_alert" -m "med_alert"