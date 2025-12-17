# Publish violation alerts periodically with random messages
messages=("Unauthorized zone entry detected" "Security perimeter breached" "Group member in restricted area" "Alert: Boundary violation")

while true; do
    random_msg=${messages[$RANDOM % ${#messages[@]}]}
    mosquitto_pub -t "/notification/violation_alert" -m "$random_msg"
    sleep 10
done &