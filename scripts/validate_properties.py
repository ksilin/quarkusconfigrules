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

def rule_matching_suffix_value_regex(properties, key_suffix, regex_pattern, treat_key_not_found_as_success=False, ignore_profiles=None):
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

def validate_numeric_range_property(properties, key_suffix, min_val=0, max_val=None, treat_key_not_found_as_success=False, ignore_profiles=None):
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

    _, a_value = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    _, b_value = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if a_value is None:
        return True, f"Property '{key_suffix_1}' is not configured; default is considered valid."

    try:
        a_numeric = float(a_value)
        b_numeric = float(b_value)
    except ValueError:
        return False, f"One of the properties '{key_suffix_1}'='{a_value}' or '{key_suffix_2}'='{b_value}' is not a valid number."

    min_val = a_numeric * min_multiple
    max_val = a_numeric * max_multiple

    if min_val <= b_numeric <= max_val:
        return True, f"Property '{key_suffix_2}' is correctly set within the range [{min_val}, {max_val}] based on '{key_suffix_1}' value of {a_numeric}."
    else:
        return False, f"Property '{key_suffix_2}'='{b_numeric}' is not within the expected range [{min_val}, {max_val}] based on '{key_suffix_1}' value of {a_numeric}."

def validate_exclusive_property_setting(properties, key_suffix_1, key_suffix_2, ignore_profiles=None):

    if ignore_profiles is None:
        ignore_profiles = []

    key_1, _ = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    key_2, _ = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if (key_1 is not None) ^ (key_2 is not None):
        return True, f"Exactly one property is set as expected: '{key_1 if key_1 else key_2}' is set."
    elif key_1 is not None and key_2 is not None:
        return False, f"Both '{key_suffix_1}' and '{key_suffix_2}' are set, but only one should be set."
    else:
        return False, f"Neither of '{key_suffix_1}' and '{key_suffix_2}' is set. One of the properties must be set."

def validate_conditional_numeric_range(properties, key_suffix_1, expected_value_1, key_suffix_2, min_val, max_val, ignore_profiles=None):
 
    key_a_full, a_value = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    if a_value != expected_value_1:
        return True, f"Property '{key_suffix_1}' is not set to '{expected_value_1}'; no validation for '{key_suffix_2}' is required."

    key_b_full, b_value = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)
    if key_b_full is None:
        return False, f"Property with suffix '{key_suffix_2}' must be set when '{key_a_full}' is '{a_value}'."

    if not is_numeric(b_value):
        return False, f"Property '{key_b_full}'='{b_value}' is not numeric and cannot be validated."

    b_numeric = float(b_value)
    if min_val <= b_numeric <= max_val:
        return True, f"Property '{key_b_full}'='{b_value}' is correctly set within the range [{min_val}, {max_val}]."
    else:
        return False, f"Property '{key_b_full}'='{b_value}' is not within the expected range [{min_val}, {max_val}], which applies when '{key_a_full}' is '{a_value}'."



def validate_properties(properties):
    errors = []

    # max.poll.records
    max_poll_records_in_range, msg = validate_numeric_range_property(properties, "max.poll.records", 1, 500, True,ignore_profiles=["dev", "test"])
    if not max_poll_records_in_range:
        errors.append(f"Property 'max.poll.records' must be numeric and within range: {msg}")

    # kafka.security.protocol
    security_protocol_sasl_ssl, msg = rule_matching_suffix_value(properties, 'kafka.security.protocol', 'SASL_SSL', ignore_profiles=["dev", "test"])
    if not security_protocol_sasl_ssl:
        errors.append(f"kafka.security.protocol: {msg}")
    
    # kafka.sasl.mechanism=PLAIN
    security_sasl_mechanism, msg = rule_matching_suffix_value(properties, 'kafka.sasl.mechanism', 'PLAIN', ignore_profiles=["dev", "test"])
    if not security_sasl_mechanism:
        errors.append(f"kafka.sasl.mechanism: {msg}")

    # kafka.sasl.jaas.config
    sasl_jaas_config, msg = rule_matching_suffix_value_regex(properties, 'kafka.sasl.jaas.config', r'org.apache.kafka.common.security.plain.PlainLoginModule required.+', ignore_profiles=["dev", "test"])
    if not sasl_jaas_config:
        errors.append(f"kafka.sasl.jaas.config: {msg}")

    # acks
    acks_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.acks", "all",ignore_profiles=["dev", "test"])
    if not acks_success:
        errors.append(f"kafka-streams.producer.acks NOT set to 'all'. {msg}") 

    # compression
    compression_success, msg = rule_matching_suffix_value(properties, "kafka-streams.producer.compression.type", ["snappy", "zstd", "lz4"],ignore_profiles=["dev", "test"])
    if not compression_success:
        errors.append(f"kafka-streams.producer.compression.type: {msg}") 

    # request timeout
    request_and_api_timeout_success, msg = validate_numeric_property_relation(properties, "request.timeout.ms", "default.api.timeout.ms", 1.5, 5, ignore_profiles=["dev", "test"])
    if not request_and_api_timeout_success:
        errors.append(f"request.timeout.ms & default.api.timeout.ms: {msg}") 

    # min.insync.replicas
    min_insync_replicas, msg = validate_numeric_range_property(properties, "kafka-streams.topic.min.insync.replicas", 3, 3, True, ignore_profiles=["dev", "test"])
    if not min_insync_replicas:
        errors.append(f"kafka-streams.topic.min.insync.replicas NOT left at default or set to 2. {msg}") 

    # replication factor with topic prefix
    replication_factor, msg = validate_numeric_range_property(properties, "kafka-streams.replication.factor", 3, 3, True, ignore_profiles=["dev", "test"])
    if not replication_factor:
        errors.append(f"kafka-streams.replication.factor NOT left at default or set to 3. {msg}") 

    # standby replicas
    standby_replicas, msg = validate_numeric_range_property(properties, "kafka-streams.num.standby.replicas", 1, 2, ignore_profiles=["dev", "test"])
    if not standby_replicas:
        errors.append(f"kafka-streams.num.standby.replicas NOT set to 1 or 2. {msg}") 

    # kafka-streams.metrics.recording.level=DEBUG
    metrics_recording_level, msg = rule_matching_suffix_value(properties, "kafka-streams.metrics.recording.level", "DEBUG",ignore_profiles=["dev", "test"])
    if not metrics_recording_level:
        errors.append(f"kafka-streams.metrics.recording.level: {msg}") 

    # bootstrap servers
    bootstrap_servers, msg = validate_exclusive_property_setting(properties, "kafka-streams.bootstrap-servers", "kafka.bootstrap.servers",ignore_profiles=["dev", "test"])
    if not bootstrap_servers:
        errors.append(f"Bootstrap servers: {msg}") 

    # application id
    application_id, msg = rule_matching_suffix_value_regex(properties, "kafka-streams.application-id", r'^[a-zA-Z0-9\.\-_]+$',ignore_profiles=["dev", "test"])
    if not application_id:
        errors.append(f"Application id: {msg}") 

    # topics
    topics, msg = rule_matching_suffix_value_regex(properties, "kafka-streams.topics", r'^[a-zA-Z0-9\.\-\$_,\{\}]+$',ignore_profiles=["dev", "test"])
    if not topics:
        errors.append(f"Required application topics: {msg}") 

    # state directory
    state_dir, msg = rule_matching_suffix_value_regex(properties, "kafka-streams.state.dir", r'^[a-zA-Z0-9\.\-_]+$',ignore_profiles=["dev", "test"])
    if not state_dir:
        errors.append(f"Explicit state directory: {msg}") 

    # commit.interval.ms for EOS
    eos_commit_interval, msg = validate_conditional_numeric_range(properties, "kafka-streams.processing.guarantee", "exactly_once_v2", "kafka-streams.commit.interval.ms", 200, 1000,ignore_profiles=["dev", "test"])
    if not eos_commit_interval:
        errors.append(f"Exactly-once and commit.interval.ms: {msg}") 

    # statestore caching
    statestore_caching, msg = validate_numeric_range_property(properties, "kafka-streams.statestore.cache.max.bytes", 1000000, treat_key_not_found_as_success=True, ignore_profiles=["dev", "test"])
    if not statestore_caching:
        errors.append(f"kafka-streams.statestore.cache.max.bytes NOT set to a high enough value for production. {msg}") 

    # deprecated statestore caching
    deprecated_statestore_caching, msg = validate_keys_not_ending_with(properties, "kafka-streams.cache.max.bytes.buffering")
    if not deprecated_statestore_caching:
        errors.append(f"Deprecated configuration cache.max.bytes.buffering is used. Consider using statestore.cache.max.bytes instead. {msg}") 

    # buffered.records.per.partition
    deprecated_per_partition_buffering, msg = validate_keys_not_ending_with(properties, "kafka-streams.buffered.records.per.partition")
    if not deprecated_per_partition_buffering:
        errors.append(f"Deprecated configuration buffered.records.per.partition is used. Consider using input.buffer.max.bytes instead, where applicable. {msg}")

    # metadata caching
    metadata_caching, msg = validate_numeric_range_property(properties, "kafka-streams.metadata.max.age.ms", 30000, 600000, True, ignore_profiles=["dev", "test"])
    if not metadata_caching:
        errors.append(f"kafka-streams.metadata.max.age.ms: {msg}") 

    # processing guarantee / EOS - use correct config
    exactly_once_v2, msg = rule_matching_suffix_value(properties, "kafka-streams.processing.guarantee", "exactly_once_v2" , True, ignore_profiles=["dev", "test"])
    if not exactly_once_v2:
        errors.append(f"kafka-streams.processing.guarantee NOT set to 'exactly_once_v2'. {msg}") 

    # linger.ms
    linger_ms, msg = validate_numeric_range_property(properties, "producer.linger.ms", 10, 200, ignore_profiles=["dev", "test"])
    if not linger_ms:
        errors.append(f"producer.linger.ms: {msg}") 

    # batch.size
    batch_size, msg = validate_numeric_range_property(properties, "producer.batch.size", 32768, 262144, True, ignore_profiles=["dev", "test"])
    if not batch_size:
        errors.append(f"producer.batch.size: {msg}") 

    # fetch.min.bytes
    fetch_min_bytes, msg = validate_numeric_range_property(properties, "consumer.fetch.min.bytes", 1000, 10000, True, ignore_profiles=["dev", "test"])
    if not fetch_min_bytes:
        errors.append(f"consumer.fetch.min.bytes: {msg}") 

    # fetch.max.wait.ms
    fetch_max_wait_ms, msg = validate_numeric_range_property(properties, "consumer.fetch.max.wait.ms", 100, 1000, True, ignore_profiles=["dev", "test"])
    if not fetch_max_wait_ms:
        errors.append(f"consumer.fetch.max.wait.ms: {msg}") 

    # no explicit idempotence, or true
    idempotence, msg = rule_matching_suffix_value(properties, "producer.enable.idempotence", "true", True, ignore_profiles=["dev", "test"])
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
