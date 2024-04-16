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

def rule_matching_suffix_value(properties, key_suffix, expected_values, treat_key_not_found_as_success=False, ignore_profiles=None):
    if not isinstance(expected_values, list):
        expected_values = [expected_values]

    if ignore_profiles is None:
        ignore_profiles = []

    filtered_keys = {k: v for k, v in properties.items() if not any(k.startswith(f"%{profile}") for profile in ignore_profiles)}

    key = next((k for k in filtered_keys if k.endswith(key_suffix)), None)

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

def validate_numeric_range_property(properties, key_suffix, min_val=0, max_val=None, treat_key_not_found_as_success=False, ignore_profiles=None):
    if max_val is None:
        max_val = float('inf')

    if ignore_profiles is None:
        ignore_profiles = []

    filtered_keys = {k: v for k, v in properties.items() if not any(k.startswith(f"%{profile}") for profile in ignore_profiles)}

    key = next((k for k in filtered_keys if k.endswith(key_suffix)), None)
    if key is None:
        if treat_key_not_found_as_success:
            return True, None
        else:
            return False, f"No key ending with '{key_suffix}' found"
    
    value = properties[key]
    if not is_numeric(value):
        return False, f"Value '{value}' for key '{key}' is not numeric'"

    value = float(value)
    in_range = min_val <= value <= max_val
    if in_range:
      return True, None
    else:
        return False, f"Value '{value}' for key `{key}` is outside the expected range of {min_val}-{max_val}"


def validate_properties(properties):
    errors = []

    # if not rule_application_id_or_client_id_defined(properties):
    #    errors.append("Either 'kafka-streams.application-id' or '*client.id' must be defined.")

    max_poll_records_in_range, msg = validate_numeric_range_property(properties, "max.poll.records", 1, 500, True,ignore_profiles=["dev", "test"])
    if not max_poll_records_in_range:
        errors.append(f"Property 'max.poll.records' must be numeric and within range: {msg}")

    max_records_success, msg = rule_matching_suffix_value(properties, 'kafka.security.protocol', 'SASL_SSL', ignore_profiles=["dev", "test"])
    if not max_records_success:
        errors.append(f"kafka.security.protocol NOT set to SASL_SSL: {msg}")

    acks_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.acks", "all",ignore_profiles=["dev", "test"])
    if not acks_success:
        errors.append(f"kafka-streams.producer.acks NOT set to 'all'. {msg}") 

    compression_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.compression.type", ["snappy", "zstd", "lz4"],ignore_profiles=["dev", "test"])
    if not compression_success:
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
