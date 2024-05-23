import re
import sys
from validations import validate_property_not_set, validate_value_expected, validate_value_regex, validate_value_numeric_range, validate_numeric_property_relation, validate_exclusive_property_setting, validate_conditional_numeric_range

def read_properties(file_path):
    """
    Read and parse properties from a file. Each property should be on a separate line in the format 'key=value'.
    Lines starting with '#' are treated as comments and are ignored.

    Parameters:
        file_path (str): The path to the file containing the properties.

    Returns:
        dict: A dictionary containing all the properties read from the file, where each key-value pair corresponds
              to one property defined in the file.

    Raises:
        IOError: An error occurs when the file at the specified path cannot be opened or read.
        ValueError: An error occurs if any line in the file does not match the expected 'key=value' format.
    """
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
        
   # kafka-streams.retries - not set, or Integer.MAX_VALUE (2147483647)
    retries, msg = validate_value_expected(properties, "kafka-streams.retries", 2147483647 ,True, ignore_profiles=["dev", "test"])
    if not retries:
        errors.append(f"kafka-streams.retries: {msg}") 
        
       # delivery.timeout.ms - set to Integer.MAX_VALUE (2147483647)
    delivery_timeout, msg = validate_value_expected(properties, "producer.delivery.timeout.ms", 2147483647 , ignore_profiles=["dev", "test"])
    if not delivery_timeout:
        errors.append(f"producer delivery.timeout.ms: {msg}") 
        
        
    # client.dns.lookup - set to use_all_dns_ips
    dns_lookup, msg = validate_value_expected(properties, "client.dns.lookup", "use_all_dns_ips", ignore_profiles=["dev", "test"])
    if not dns_lookup:
        errors.append(f"client.dns.lookup: {msg}") 
        
    # session.timeout.ms
    session_timeout, msg = validate_value_numeric_range(properties, "consumer.session.timeout.ms", 30000, 300000, True, ignore_profiles=["dev", "test"])
    if not session_timeout:
        errors.append(f"Consumer session.timeout.ms: {msg}") 
        
    # heartbeat.interval.ms
    heartbeat_interval, msg = validate_value_numeric_range(properties, "consumer.heartbeat.interval.ms", 3000, 30000, True, ignore_profiles=["dev", "test"])
    if not heartbeat_interval:
        errors.append(f"Consumer heartbeat.interval.ms: {msg}") 
       
    # relation between session.timeout.ms and heartbeat.interval.ms 
    heartbeat_interval_session_timeout_relation, msg = validate_numeric_property_relation(properties, "consumer.session.timeout.ms", "consumer.heartbeat.interval.ms", 0.1, 0.33, ignore_profiles=["dev", "test"])
    if not heartbeat_interval_session_timeout_relation:
        errors.append(f"Consumer session.timeout.ms & heartbeat.interval.ms: {msg}") 
        
    # connections.max.idle.ms
    connections_idle, msg = validate_value_numeric_range(properties, "connections.max.idle.ms", 120000, 240000, ignore_profiles=["dev", "test"])
    if not connections_idle:
        errors.append(f"connections.max.idle.ms: {msg}")     

    # deserialization exception handler
    deserialization_handler, msg = validate_value_expected(properties, "kafka-streams.default.deserialization.exception.handler", ["kafka.streams.errors.LogAndFailDeserializationHandler", "com.example.CustomDeserializationExceptionHandler"], True, ignore_profiles=["dev", "test"])
    if not deserialization_handler:
        errors.append(f"Default deserialization exception handler: {msg}")     


    # production exception handler
    production_handler, msg = validate_property_not_set(properties, "kafka-streams.default.production.exception.handler")
    if not production_handler:
        errors.append(f"The configuration 'default.production.exception.handler' is set unexpectedly. Please clarify the requirement with your application team, before changing this configuration. {msg}")


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
