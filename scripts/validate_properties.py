import re
import sys

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

def validate_keys_not_ending_with(data_dict, suffix):
    for key in data_dict.keys():
        if str(key).endswith(suffix):
            return False, f"Expected {key} to not be set. It is set to {data_dict[key]}."
    return True, None

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

def is_numeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def rule_max_poll_records(properties):
    key = next(filter(lambda k: k.endswith('max.poll.records'), properties.keys()), None)
    if key is None: return True
    if key is not None:
        max_records = properties[key]
        return is_numeric(max_records) and int(max_records) <= 1000
    return False

def validate_properties(properties):
    errors = []

    # if not rule_application_id_or_client_id_defined(properties):
    #    errors.append("Either 'kafka-streams.application-id' or '*client.id' must be defined.")

    if not rule_max_poll_records(properties):
        errors.append("Property 'max.poll.records' must be numeric and <= 10000.")

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
    default_file_path = 'src/main/resources/application.properties'
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file_path
    properties = read_properties(file_path)
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
