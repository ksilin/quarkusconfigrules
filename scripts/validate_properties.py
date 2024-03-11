import re

def read_properties(file_path):
    properties = {}
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip() and not line.startswith('#'):
                try:
                  key, value = line.strip().split('=', 1)
                  properties[key.strip()] = value.strip()
                except ValueError:
                  print(f"Error processing line {line_number}: '{line.strip()}' does not match 'key=value' format.")
    return properties

def is_numeric(value):
    return value.isdigit()

# TODO - return offending value 
def rule_matching_suffix_value1(properties, key_suffix, expected_value):
    key = next(filter(lambda k: k.endswith(key_suffix), properties.keys()), None)
    if key is not None:
        return properties[key] == expected_value
    return False

def rule_matching_suffix_value(properties, key_suffix, expected_values, treat_key_not_found_as_success=False):
    if not isinstance(expected_values, list):
        expected_values = [expected_values]

    key = next((k for k in properties.keys() if k.endswith(key_suffix)), None)

    if key is not None:
        if properties[key] in expected_values:
            return True, (key, properties[key])
        else:
            return False, f"{key} found but set to '{properties[key]}', expected {expected_values}"
    else:
        if treat_key_not_found_as_success:
            return True, None
        else:
            return False, f"No key ending with '{key_suffix}' found"


def rule_max_records(properties):
    key = next(filter(lambda k: k.endswith('max.records'), properties.keys()), None)
    if key is None: return True
    if key is not None:
        max_records = properties[key]
        return is_numeric(max_records) and int(max_records) <= 10000
    return False

def rule_timeout_and_backoff(properties):
    timeout = properties.get('timeout')
    max_records = properties.get('max.records')
    backoff = properties.get('backoff')

    if timeout:
        if not timeout.isdigit() or (max_records and int(timeout) >= int(max_records)):
            return False
        if backoff is None or backoff.lower() not in ['true', 'false']:
            return False
    elif backoff and backoff.lower() not in ['true', 'false']:
        return False
    return True

def validate_properties(properties):
    errors = []

    # if not rule_application_id_or_client_id_defined(properties):
    #    errors.append("Either 'kafka-streams.application-id' or '*client.id' must be defined.")

    if not rule_max_records(properties):
        errors.append("Property 'max.records' must be numeric and <= 10000.")

    if not rule_timeout_and_backoff(properties):
        errors.append("Rules for 'timeout' and 'backoff' failed.")

    max_records_success, msg = rule_matching_suffix_value(properties, 'kafka.security.protocol', 'SASL_SSL')
    if not max_records_success:
        errors.append(f"kafka.security.protocol NOT set to SASL_SSL: {msg}")

    acks_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.acks", "all")
    if not acks_success:
        errors.append(f"kafka-streams.producer.acks NOT set to 'all'. {msg}") 

    acks_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.compression.type", ["snappy", "zstd", "lz4"])
    if not acks_success:
        errors.append(f"kafka-streams.producer.compression.type: {msg}") 

    return errors

def main():
    properties = read_properties('src/main/resources/application.properties')
    errors = validate_properties(properties)

    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"- {error}")
        exit(1)
    else:
        print("Validation successful. No errors found.")

if __name__ == "__main__":
    main()
