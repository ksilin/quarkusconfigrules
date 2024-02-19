#!/bin/bash

APP_PROPERTIES="src/main/resources/application.properties"

check_property() {
    local property="$1"
    local expected_value="$2"
    local actual_value=$(grep "^${property}=" "$APP_PROPERTIES" | cut -d'=' -f2-)

    if [ "$actual_value" != "$expected_value" ]; then
        echo "Verification failed: ${property} is not set to ${expected_value}. Current value: ${actual_value}"
        exit 1
    fi
}

check_numeric_property_greater_than() {
    local property="$1"
    local expected_value="$2"
    local actual_value=$(grep "^${property}=" "$APP_PROPERTIES" | cut -d'=' -f2-)

    if ! [[ "$actual_value" =~ ^[0-9]+$ ]]; then
        echo "Verification failed: ${property} is not a number. Current value: ${actual_value}"
        exit 1
    fi

    if [ "$actual_value" -le "$expected_value" ]; then
        echo "Verification failed: ${property} is not greater than ${expected_value}. Current value: ${actual_value}"
        exit 1
    fi
}

# Check specific properties
check_property "kafka-streams.producer.acks" "all"
check_property "kafka-streams.producer.compression.type" "lz4"
check_numeric_property_greater_than "kafka-streams.num.standby.replicas" 1

echo "All verifications passed."