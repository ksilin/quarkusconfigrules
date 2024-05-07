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

def validate_property_not_set(properties, key_suffix):
    for key in properties.keys():
        if str(key).endswith(key_suffix):
            return False, f"Expected {key} to not be set. It is set to {properties[key]}."
    return True, None

def validate_value_expected(properties, key_suffix, expected_values, treat_key_not_found_as_success=False, ignore_profiles=None):
    if not isinstance(expected_values, list):
        expected_values = [expected_values]

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key:
        if value in expected_values:
            return True, (key, value)
        else:
            return False, f"{key} found but set to '{value}', expected {expected_values}"
    else:
        if treat_key_not_found_as_success:
            return True, None
        else:
            return False, f"No key ending with '{key_suffix}' found"

def validate_value_regex(properties, key_suffix, regex_pattern, treat_key_not_found_as_success=False, ignore_profiles=None):
    if ignore_profiles is None:
        ignore_profiles = []

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key:
        if re.match(regex_pattern, value):
            return True, (key, value)
        else:
            return False, f"Value '{value}' for key '{key}' does not match the required pattern: {regex_pattern}"
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

def validate_value_numeric_range(properties, key_suffix, min_val=0, max_val=None, treat_key_not_found_as_success=False, ignore_profiles=None):
    if max_val is None:
        max_val = float('inf')

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key is None:
        if treat_key_not_found_as_success:
            return True, None
        else:
            return False, f"No key ending with '{key_suffix}' found"

    if not is_numeric(value):
        return False, f"Value '{value}' for key '{key}' is not numeric"

    value = float(value)
    in_range = min_val <= value <= max_val
    if in_range:
        return True, None
    else:
        return False, f"Value '{value}' for key `{key}` is outside of the expected range [{min_val},{max_val}]"

def get_key_value_by_suffix(properties, key_suffix, ignore_profiles=None):
    if ignore_profiles is None:
        ignore_profiles = []

    filtered_keys = {
        k: v for k, v in properties.items()
        if not any(k.startswith(f"%{profile}") for profile in ignore_profiles)
        and k.endswith(key_suffix)
    }

    key = next(iter(filtered_keys), None)
    return (key, filtered_keys.get(key)) if key else (None, None)

def validate_numeric_property_relation(properties, key_suffix_1, key_suffix_2, min_multiple, max_multiple, ignore_profiles=None):

    key_1, value_1 = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    key_2, value_2 = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if value_1 is None:
        return True, f"Property '{key_suffix_1}' is not configured; default is considered valid."

    try:
        numeric_1 = float(value_1)
        numeric_2 = float(value_2)
    except ValueError:
        return False, f"One of the properties '{key_1}'='{value_1}' or '{key_2}'='{value_2}' is not a valid number."

    min_val = numeric_1 * min_multiple
    max_val = numeric_1 * max_multiple

    if min_val <= numeric_2 <= max_val:
        return True, f"Property '{key_2}' is correctly set within the range [{min_val}, {max_val}] based on '{key_1}' value of {numeric_1}."
    else:
        return False, f"Property '{key_2}'='{numeric_2}' is not within the expected range [{min_val}, {max_val}] based on '{key_1}' value of {numeric_1}."

def validate_exclusive_property_setting(properties, key_suffix_1, key_suffix_2, ignore_profiles=None):

    if ignore_profiles is None:
        ignore_profiles = []

    key_1, _ = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    key_2, _ = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if (key_1 is not None) ^ (key_2 is not None):
        return True, f"Exactly one property is set as expected: '{key_1 if key_1 else key_2}' is set."
    elif key_1 is not None and key_2 is not None:
        return False, f"Both '{key_1}' and '{key_2}' are set, but only one should be set."
    else:
        return False, f"Neither of '{key_suffix_1}' and '{key_suffix_2}' is set. One of the properties must be set."

def validate_conditional_numeric_range(properties, key_suffix_1, expected_value_1, key_suffix_2, min_val, max_val, ignore_profiles=None):
    """
    Validate that if one property is set to a specific value, then second property must be within a defined numeric range.

    Parameters:
        properties (dict): Dictionary containing property keys and values.
        key_suffix_1 (str): Key suffix for the first property.
        expected_value_1 (str): The specific value of property first property that triggers validation for second property.
        key_b_suffix (str): Key suffix for second property - the one being evaluated against the range.
        min_val (float): Minimum valid value for second property.
        max_val (float): Maximum valid value for second property.
        ignore_profiles (list, optional): Profiles to ignore in key searching.

    Returns:
        tuple: (bool, str) indicating whether the property value is valid and a message describing the result.
    """
    key_1, value_1 = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    if value_1 != expected_value_1:
        return True, f"Property '{key_1}' is not set to '{expected_value_1}'; no validation for '{key_suffix_2}' is required."

    key_2, value_2 = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)
    if key_2 is None:
        return False, f"Property with suffix '{key_suffix_2}' must be set when '{key_1}' is '{value_1}'."

    if not is_numeric(value_2):
        return False, f"Property '{key_2}'='{value_2}' is not numeric and cannot be validated."

    b_numeric = float(value_2)
    if min_val <= b_numeric <= max_val:
        return True, f"Property '{key_2}'='{value_2}' is correctly set within the range [{min_val}, {max_val}]."
    else:
        return False, f"Property '{key_2}'='{value_2}' is not within the expected range [{min_val}, {max_val}], which applies when '{key_1}' is '{value_1}'."


def validate_properties(properties):
    errors = []

    # max.poll.records
    max_poll_records_in_range, msg = validate_value_numeric_range(properties, "max.poll.records", 1, 500, True,ignore_profiles=["dev", "test"])
    if not max_poll_records_in_range:
        errors.append(f"Property 'max.poll.records' must be numeric and within range: {msg}")

    # kafka.security.protocol
    security_protocol_sasl_ssl, msg = validate_value_expected(properties, 'kafka.security.protocol', 'SASL_SSL', ignore_profiles=["dev", "test"])
    if not security_protocol_sasl_ssl:
        errors.append(f"kafka.security.protocol: {msg}")
    
    # kafka.sasl.mechanism=PLAIN
    security_sasl_mechanism, msg = validate_value_expected(properties, 'kafka.sasl.mechanism', 'PLAIN', ignore_profiles=["dev", "test"])
    if not security_sasl_mechanism:
        errors.append(f"kafka.sasl.mechanism: {msg}")

    # kafka.sasl.jaas.config
    sasl_jaas_config, msg = validate_value_regex(properties, 'kafka.sasl.jaas.config', r'org.apache.kafka.common.security.plain.PlainLoginModule required.+', ignore_profiles=["dev", "test"])
    if not sasl_jaas_config:
        errors.append(f"kafka.sasl.jaas.config: {msg}")

    # acks
    acks_success, msg = validate_value_expected(properties, "kafka-streams.producer.acks", "all",ignore_profiles=["dev", "test"])
    if not acks_success:
        errors.append(f"kafka-streams.producer.acks NOT set to 'all'. {msg}") 

    # compression
    compression_success, msg = validate_value_expected(properties, "kafka-streams.producer.compression.type", ["snappy", "zstd", "lz4"],ignore_profiles=["dev", "test"])
    if not compression_success:
        errors.append(f"kafka-streams.producer.compression.type: {msg}") 

    # request timeout
    request_and_api_timeout_success, msg = validate_numeric_property_relation(properties, "request.timeout.ms", "default.api.timeout.ms", 1.5, 5, ignore_profiles=["dev", "test"])
    if not request_and_api_timeout_success:
        errors.append(f"request.timeout.ms & default.api.timeout.ms: {msg}") 

    # min.insync.replicas
    min_insync_replicas, msg = validate_value_numeric_range(properties, "kafka-streams.topic.min.insync.replicas", 3, 3, True, ignore_profiles=["dev", "test"])
    if not min_insync_replicas:
        errors.append(f"kafka-streams.topic.min.insync.replicas NOT left at default or set to 2. {msg}") 

    # replication factor with topic prefix
    replication_factor, msg = validate_value_numeric_range(properties, "kafka-streams.replication.factor", 3, 3, True, ignore_profiles=["dev", "test"])
    if not replication_factor:
        errors.append(f"kafka-streams.replication.factor NOT left at default or set to 3. {msg}") 

    # standby replicas
    standby_replicas, msg = validate_value_numeric_range(properties, "kafka-streams.num.standby.replicas", 1, 2, ignore_profiles=["dev", "test"])
    if not standby_replicas:
        errors.append(f"kafka-streams.num.standby.replicas NOT set to 1 or 2. {msg}") 

    # kafka-streams.metrics.recording.level=DEBUG
    metrics_recording_level, msg = validate_value_expected(properties, "kafka-streams.metrics.recording.level", "DEBUG",ignore_profiles=["dev", "test"])
    if not metrics_recording_level:
        errors.append(f"kafka-streams.metrics.recording.level: {msg}") 

    # bootstrap servers
    bootstrap_servers, msg = validate_exclusive_property_setting(properties, "kafka-streams.bootstrap-servers", "kafka.bootstrap.servers",ignore_profiles=["dev", "test"])
    if not bootstrap_servers:
        errors.append(f"Bootstrap servers: {msg}") 

    # application id
    application_id, msg = validate_value_regex(properties, "kafka-streams.application-id", r'^[a-zA-Z0-9\.\-_]+$',ignore_profiles=["dev", "test"])
    if not application_id:
        errors.append(f"Application id: {msg}") 

    # topics
    topics, msg = validate_value_regex(properties, "kafka-streams.topics", r'^[a-zA-Z0-9\.\-\$_,\{\}]+$',ignore_profiles=["dev", "test"])
    if not topics:
        errors.append(f"Required application topics: {msg}") 

    # state directory
    state_dir, msg = validate_value_regex(properties, "kafka-streams.state.dir", r'^[a-zA-Z0-9\.\-_]+$',ignore_profiles=["dev", "test"])
    if not state_dir:
        errors.append(f"Explicit state directory: {msg}") 

    # commit.interval.ms for EOS
    eos_commit_interval, msg = validate_conditional_numeric_range(properties, "kafka-streams.processing.guarantee", "exactly_once_v2", "kafka-streams.commit.interval.ms", 200, 1000,ignore_profiles=["dev", "test"])
    if not eos_commit_interval:
        errors.append(f"Exactly-once and commit.interval.ms: {msg}") 

    # statestore caching
    statestore_caching, msg = validate_value_numeric_range(properties, "kafka-streams.statestore.cache.max.bytes", 1000000, treat_key_not_found_as_success=True, ignore_profiles=["dev", "test"])
    if not statestore_caching:
        errors.append(f"kafka-streams.statestore.cache.max.bytes NOT set to a high enough value for production. {msg}") 

    # deprecated statestore caching
    deprecated_statestore_caching, msg = validate_property_not_set(properties, "kafka-streams.cache.max.bytes.buffering")
    if not deprecated_statestore_caching:
        errors.append(f"Deprecated configuration cache.max.bytes.buffering is used. Consider using statestore.cache.max.bytes instead. {msg}") 

    # buffered.records.per.partition
    deprecated_per_partition_buffering, msg = validate_property_not_set(properties, "kafka-streams.buffered.records.per.partition")
    if not deprecated_per_partition_buffering:
        errors.append(f"Deprecated configuration buffered.records.per.partition is used. Consider using input.buffer.max.bytes instead, where applicable. {msg}")

    # metadata caching
    metadata_caching, msg = validate_value_numeric_range(properties, "kafka-streams.metadata.max.age.ms", 30000, 600000, True, ignore_profiles=["dev", "test"])
    if not metadata_caching:
        errors.append(f"kafka-streams.metadata.max.age.ms: {msg}") 

    # processing guarantee / EOS - use correct config
    exactly_once_v2, msg = validate_value_expected(properties, "kafka-streams.processing.guarantee", "exactly_once_v2" , True, ignore_profiles=["dev", "test"])
    if not exactly_once_v2:
        errors.append(f"kafka-streams.processing.guarantee NOT set to 'exactly_once_v2'. {msg}") 

    # linger.ms
    linger_ms, msg = validate_value_numeric_range(properties, "producer.linger.ms", 10, 200, ignore_profiles=["dev", "test"])
    if not linger_ms:
        errors.append(f"producer.linger.ms: {msg}") 

    # batch.size
    batch_size, msg = validate_value_numeric_range(properties, "producer.batch.size", 32768, 262144, True, ignore_profiles=["dev", "test"])
    if not batch_size:
        errors.append(f"producer.batch.size: {msg}") 

    # fetch.min.bytes
    fetch_min_bytes, msg = validate_value_numeric_range(properties, "consumer.fetch.min.bytes", 1000, 10000, True, ignore_profiles=["dev", "test"])
    if not fetch_min_bytes:
        errors.append(f"consumer.fetch.min.bytes: {msg}") 

    # fetch.max.wait.ms
    fetch_max_wait_ms, msg = validate_value_numeric_range(properties, "consumer.fetch.max.wait.ms", 100, 1000, True, ignore_profiles=["dev", "test"])
    if not fetch_max_wait_ms:
        errors.append(f"consumer.fetch.max.wait.ms: {msg}") 

    # no explicit idempotence, or true
    idempotence, msg = validate_value_expected(properties, "producer.enable.idempotence", "true", True, ignore_profiles=["dev", "test"])
    if not idempotence:
        errors.append(f"producer.enable.idempotence: {msg}") 

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
