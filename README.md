# quarkusconfig

The purpose of this project is to provide enforceable guidelines on application configurations. 
In its first iteration, specifically on Kafka Streams applications created with the Quarkus framework. 

The assumption is that the configuration is contained in the `src/resources/application.properties` file. 

## Rules

There are several types of rules: 

Some enforce a value or one of many possible values, or a value range. 
Some enforce a reasonable cooperation of values.  
Some enforce that once a default value has been overridden, it is done on purpose, and with a reasonable alternative. 

### Enforcing a value or value range

* Value 

When working with Confluent Cloud, the value for the security protocol always needs to be set to `SASL_SSL`. 

* One value of many 

When deciding on one of many options, e.g. compression algorithm, the decision depends on the data and should be the result of benchmarking. 
We might decide to allow `snappy` and `lz4`, while disallowing `gzip` and `zstd`.  

* Value range

We might decide to override `max.poll.records`, to reduce or increase the number of records processed per poll loop. But these changes need to happen in a reasonable range.


### Enforcing value combination example

Consumer configuration:

`default.api.timeout.ms` defaults to 60 seconds.

`request.timeout.ms` defaults to 30 seconds.

Some applications override/increase the request timeout, in order to be able to handle longer outages. However, they might forget to also increase the default API timeout.   

The default API timeout value should be greater than the request timeout in order to be able to gracefully handle errors, e.g. committing offsets in an exception handler.  
If this is not the case, the application will timeout immediately, after the request timeout threshold has been reached. 

### Defaults are fine, overrides need to be coordinated

The default deserialization exception handler will fail on a message it cannot read, bringing down the instance. In many cases, this is the expected behavior. However, we might want to rather skip the record and continue. 

This decision needs to be communicated and agreed upon, so by default, overriding the handler is not allowed. The ruel can be disabled for a project, once consensus has been reached.  

## Details

### Error aggregation

While we value rapid feeback, complete feedback is even more preferable. We do not fail on the first rule violation. We aggregate all violations, so they can be fixed all at once, saving precious cycle time. 


### Profies and prefixes

The Quarkus framework offers the possiblity to work with multiple profiles. In the configuration files, the properties are then prefixed with the profile name, e.g. 

`%prod.kafka.sasl.mechanism=PLAIN`

For correct functionality, we need to check the configurations ending in the expected string.  

## Rules

### setting a reasonable `max.poll.records`

The default setting of `1000` might be too high and lead to consumer session timeouts.
If you are noticing frequent rebalances, consider identifying a safe value.  

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L1200

### `kafka.security.protocol` must be set to `SASL_SSL`

This is the default for Confluent Cloud applications. 

If not set, client might attempt connecting to the cluster using a plaintext protocol, failing the SSL handshake and retrying, effectively trying to DoS the clsuter.  


### setting `kafka-streams.producer.acks` to `all`

The default for Kafka Streams is `1`. This can potentially lead to data loss, if the leader immediately fails after acknowledging the record, but before the followers have replicated it. The recommended value is `all`


### setting `kafka-streams.producer.compression.type`to one of the values "snappy", "zstd", or "lz4"

It is generally recommended to use producer compression. It is not active by default. 
Among the available algorithms, `gzip` has the highest CPU cost and can be safely discouraged in favor of the other algorithms. 

### Replication factor is either default or 3

The default value of `-1` (default to broker config) is sufficient to provide internal topics with the same availability guarantee we expect from all topics.

If explicitly set, the recommended value is `3`, in line with other topics. 

### Setting standby replicas

The default setting is `0`. 

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L846

### enabling metrics with `kafka-streams.metrics.recording.level=DEBUG`

The default metrics level is `INFO`. Some important metrics are only collected if `DEBUG` level is activated, e.g. most task-level, state store, and record cache metrics.

https://docs.confluent.io/platform/current/streams/monitoring.html

### Ensuring `quarkus.kafka-streams.bootstrap-servers` is set

This configuration is required for the applicaiton to start.  

### Ensuring `quarkus.kafka-streams.application-server`is set


### Ensuring `quarkus.kafka-streams.topics`is set

Quarkus offers a safeguard, which prevents the Kafka Streams application from starting, unless the configured topics exist on the cluster. 
This configuration is beneficial, so we are requiring it to be set to a non-empty string.  

### Ensuring `state.dir` is set explicitly

By default, the state is stored in `/${java.io.tmpdir}/kafka-streams`. This might not be where you want the state to be set, as the default tempdir will be purged on system restart.

It is thus recommended to use a dedicated configuration for the state directory

We do not care about this config for `%dev` and `%test` profiles.

### Throughput-friendly caching - `kafka-streams.cache.max.bytes.buffering`

The Quarkus Kafka Streams tutorial recommends setting the value to `10240`. This is good for testing, as records are progressing through the topology quickly. For production, higher values are recommended.

In our setup, we are expecting this value to be either left at the default value of `10485760`, or set to a value over `1000000`.

We do not care about this config for `%dev` and `%test` profiles.

https://quarkus.io/guides/kafka-streams

### Commit interval for at-least-once-processing: kafka-streams.commit.interval.ms=1000

### Prevent excessive metadata requests: `kafka-streams.metadata.max.age.ms`

The Quarkus Kafka Streams tutorial recommends setting the value to `500`. This is fine for testing, where we need quick propagation od metadata changes. However, in production, we are either leaving this configuration it its deault (5 minutes), or setting it to a reasonably high value of 30+ sec. 

We do not care about this config for `%dev` and `%test` profiles.

https://quarkus.io/guides/kafka-streams

### EOS - use the right version

The only recommended version is `exactly_once_v2`. Other values, such as `exactly_once` and `exactly_one_beta` are deprecated and will be removed.  



#### if EOS is used, do not use separate ack config

### If explicitly setting linger.ms, do not use exreme values

The default is `100`, optimized for low latency.
For high throughput, consider increasing the value, accompanied by continuous testing. 
A value between `10` and `200` ms is required in our setup. 

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L1182

### explicitly set batch.size

The default is `16384`, optimized for low latency.
For a higher throughput, consider increasing the value, accompanied by continuous testing. 
A value between `32768` and `262144` ms is required in our setup. 

### consumer fetch.min.bytes

Is `1` by default. The default is fine for low latency and low throughput applications. 
With increasing throughput, you will benefit from the consumer waiting for a little longer to collect more records (up to the max of `fetch.max.wait.ms = 500`), resulting in a lower number of calls to the cluster and overhead for fetch processing.    

In our example, we are setting this configuration to `10000` bytes.


## Testing the rules 

You can test the rules on your properties file:

`python ./scripts/validate_properties.py <path_to_properies_file>`

If no path is provided as an argument, the default `src/main/resources.properties` will be used. 


## TODOs

* profile-specific rules

