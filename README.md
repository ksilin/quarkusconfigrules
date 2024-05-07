# quarkusconfig

The purpose of this project is to provide enforceable guidelines on application configurations. 
In its first iteration, specifically on Kafka Streams applications created with the Quarkus framework. 

The assumption is that the configuration is contained in the `src/resources/application.properties` file. 

## Rules

There are several types of rules: 

Some enforce a value or one of many possible values, a value range or a regex match. 
Some enforce a reasonable cooperation of values.  
Some enforce that once a default value has been overridden, it is done on purpose, and with a reasonable alternative. 

### Enforcing a value or value range

* Single value 

When working with Confluent Cloud, the value for the security protocol always needs to be set to `SASL_SSL`. 

* One value of many 

When deciding on one of many options, e.g. compression algorithm, the decision depends on the data and should be the result of benchmarking. 
We might decide to allow `snappy` and `lz4`, while disallowing `gzip` and `zstd`.  

* Value range

We might decide to override `max.poll.records`, to reduce or increase the number of records processed per poll loop. But these changes need to happen in a reasonable range.

* Value regular expression

Some values, such as topic names can only be checked for plausibility, not concrete values. For this purpose, regex matching validations are used. 

### Enforcing property combinations

* Value as a range of multiples of another value

Consumer configuration:

`default.api.timeout.ms` defaults to 60 seconds.

`request.timeout.ms` defaults to 30 seconds.

Some applications override/increase the request timeout, in order to be able to handle longer outages. However, they might forget to also increase the default API timeout.   

The default API timeout value should be greater than the request timeout in order to be able to gracefully handle errors, e.g. committing offsets in an exception handler.  
If this is not the case, the application will timeout immediately, after the request timeout threshold has been reached. 

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#request-timeout-ms

* Only one of multiple properties can be set

Quarkus offers multiple ways fo setting the same parameters. Either one of those can be used. Using multiple properties in the same file may lead to uneecessary confusion. 

* Conditional numeric range

Some properties imply changes in others. For example, enabling exactly-once processing implicitly changes commit intervals and further producer properties.

This has the effect that the applicable value range of one property only applies if a different property has been set to a certain value.  

### Other rules

* Enforcing NOT setting a preperty

This is useful to prevent applcations from using deprecated properties, which will be removed in the future, or prevent reasonable defaults from being overwritten.  

### Defaults are fine, overrides need to be coordinated

The default deserialization exception handler will fail on a message it cannot read, bringing down the instance. In many cases, this is the expected behavior. However, we might want to rather skip the record and continue. 

This decision needs to be communicated and agreed upon, so by default, overriding the handler is not allowed. The ruel can be disabled for a project, once consensus has been reached.  

### Implementation and application

The validations are implemented in a generic way, to be applied to multiple existing rules, as well as potential further rules in the future.  

The implementation of generic rules can be found in the `scripts/validations.py` file.

The application of concrete rules can be found in the `scripts/validate_properties.py` file. 

## Details

### Error aggregation

While we value rapid feeback, complete feedback is even more preferable. We do not fail on the first rule violation. We aggregate all violations, so they can be fixed all at once, saving precious cycle time. 


### Profies and prefixes

The Quarkus framework offers the possiblity to work with multiple profiles. In the configuration files, the properties are then prefixed with the profile name, e.g. 

`%prod.kafka.sasl.mechanism=PLAIN`

For correct functionality, we need to check the configurations ending in the expected string.  

The rules allow for ignoring any violations in certain profiles. By default, properties in the `dev` and `test` profiles are not checked for violations. This can be changed per rule check.

## Rules

### Increased client stability, resilience, availability

Some rules are difficult to put into a sungle bucket, as many rules aim on reducing the number of requests and makign individual requests more efficient. This can hava a positive impact on the throughput of the application, but at the same time reduces the burden on the cluster, by reducing the total amount of requests.

#### Set a reasonable `max.poll.records` limit

The default setting of `1000` might be too high and lead to consumer session timeouts.
If you are noticing frequent rebalances, consider identifying a safe value.  

In our example, we are checking for a range between `1` and `500`.

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L1200

#### Set `kafka-streams.producer.acks` to `all`

The default for Kafka Streams is `1`. This can potentially lead to data loss, if the leader immediately fails after acknowledging the record, but before the followers have replicated it. The recommended value is `all`.

The value of `all` is automatically applied with exactly-once processing and is then technically redundant. There is no downside in having it set to `all` explicitly at all times.  

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#recommended-configuration-parameters-for-resiliency

#### Set `kafka-streams.producer.compression.type`to one of the values `snappy`, `zstd`, or `lz4`

It is generally recommended to use producer compression. It is not active by default. 
Among the available algorithms, `gzip` has the highest CPU cost and can be safely discouraged in favor of the other algorithms. 
Deciding between the remaining three is often a matter of experimatation, as they perfom differently depending on multiple factors. 

https://www.confluent.io/blog/apache-kafka-message-compression/

#### Set `kafka-streams.topic.min.insync.replicas` to `2`

 The minimum number of replicas to acknowledge producer writes. Topics on Confluent Cloud allow this setting to be `1` or `2`. The default and the recommended value to use with Confluent Cloud is `2`. Lower values can potentially lead to data loss, if the leader immediately fails after acknowledging the record, but before the followers have replicated it.

 The value can remain unset. 

 Be mindful of the `TopicPrefix`: https://github.com/confluentinc/kafka/blob/v7.6.1/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L177

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#recommended-configuration-parameters-for-resiliency

#### Topic replication factor is either default or 3 - `kafka-streams.replication.factor`

The default value of `-1` (default to broker config) is sufficient to provide internal topics with the same availability guarantee we expect from all topics.

If explicitly set, the recommended value is `3`, in line with other topics. 

The value can remain unset. 

https://docs.confluent.io/platform/current/installation/configuration/streams-configs.html#replication-factor

#### Setting standby replicas - `kafka-streams.num.standby.replicas`

Standby replicas are copies of local state stores, used to minimize the latency of task failovers. 

The default setting is `0`. 

For most applications, we recommend increasing the number of standby replicas to `1`. We rarely see or recommend using more than `2`. 

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L846

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#streams-developer-guide-standby-replicas

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#recommended-configuration-parameters-for-resiliency

#### Ensuring `kafka-streams.state.dir` is set explicitly

By default, the state is stored in `/${java.io.tmpdir}/kafka-streams`. This might not be where you want the state to be set, as the default tempdir will be purged on system restart.

It is thus recommended to use a dedicated configuration for the state directory. 

We are using a simple regex, same as for the application id: `r'^[a-zA-Z0-9\.\-_]+$'`

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#state-dir

#### Exactly-once processing (EOS) - use the right version for `processing.guarantee`

The only recommended version is `exactly_once_v2`. Other values, such as `exactly_once` and `exactly_one_beta` are deprecated and will be removed. The default value of `at_least_once` can, but should not be set explicitly. 

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#optional-configuration-parameters

#### Commit interval for at-least-once-processing: `kafka-streams.commit.interval.ms`

The defaults are `30000` for at-least-once processing, and `100` for `exactly_once_v2`. 

If EOS is used, `100` ms might be too short, potentially resulting in failures and retries. We recommend increasing the configuration to `200` to `1000` ms for EOS.

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#commit-interval-ms

#### Prevent excessive metadata requests: `kafka-streams.metadata.max.age.ms`

The Quarkus Kafka Streams tutorial recommends setting the value to `500`. This is fine for testing, where we need quick propagation od metadata changes. However, in production, we are either leaving this configuration it its default (5 minutes), or setting it to a reasonably high value of 30+ sec.

Having this property set to a low value can generate an excellsive number of metadata requests, inclreasing teh load on the client itself and the cluster. 

https://quarkus.io/guides/kafka-streams

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#metadata-max-age-ms

#### Do not configure producer idempotence explicitly, or set it to `true`.

The default for `enable.idempotence` is `true` since AK 3.1. When using older clients, setting it to `true` is recommended.

When using EOS, producer idempotence is enabled by default.

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#enable-idempotence


### Confluent Cloud requirements

#### Set `kafka.security.protocol` to `SASL_SSL`

This is the requirement for Confluent Cloud applications. 

If not set, client might attempt connecting to the cluster using a plaintext protocol, failing the SSL handshake and retrying, effectively trying to DoS the clsuter.  

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#security-protocol

#### Set `kafka.sasl.mechanism` to `PLAIN`

This is required by Confluent Cloud.

// TODO - complete


#### Use the `PlainLoginModule` in your SASL JAAS config

This is required by Confluent Cloud.


### Kafka Streams requirements

#### Ensuring `quarkus.kafka-streams.application-id`is set

This configuration is required for the application to start.

The application ID can be a combination of alphanumerics, underscore, dot and dash. We use this regex to ensure this: `r'^[a-zA-Z0-9\.\-_]+$'` . Additional checks can be added to enforce naming and versioning rules. 

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#application-id

#### Ensuring either `kafka-streams.bootstrap-servers` or `kafka.bootstrap.servers`, but not both, is set

This configuration is required for the application to start. The `kafka` variant is used for non-KStreams implementations (e.g. Smallrye Kafka Connector) and is a fallback to the `kafka-streams` variant with Kafka Streams. 

https://quarkus.pro/guides/kafka-streams.html#quarkus-kafka-streams_quarkus.kafka-streams.bootstrap-servers


### Further recommendations

#### Enabling state store and other metrics with `kafka-streams.metrics.recording.level=DEBUG`

The default metrics level is `INFO`. Some important metrics are only collected if `DEBUG` level is activated, e.g. most task-level, state store, and record cache metrics.

https://docs.confluent.io/platform/current/streams/monitoring.html

### Do not use the deprecated `cache.max.bytes.buffering` and `buffered.records.per.partition` configuration

The configuration has been renamed and is deprecated. However, many parts of the existing documentation did not catch up with the change yet. 

In the same change, the per-partition configuration `buffered.records.per.partition` (defaults to `10000`) was changed to the per-topology `input.buffer.max.bytes` (defaults to `512MB`). We do not have a recommmendation on this new configuration yet. 

The implementation is to be completed with the AK 3.8 release.

KIP-770: https://cwiki.apache.org/confluence/pages/viewpage.action?pageId=186878390
https://issues.apache.org/jira/browse/KAFKA-13152

https://quarkus.io/guides/kafka-streams


### Quarkus-specific recommendations

#### Ensuring `quarkus.kafka-streams.topics`is set to a plausible string

Quarkus offers a safeguard, which prevents the Kafka Streams application from starting, unless the configured topics exist on the cluster. 

This configuration is beneficial, so we are requiring it to be set to a non-empty, plausible string.  

Kafka topic names are restricted to alphanumerics, underscore, dot and dash. Since there can be multiple topics, we add the comma, the dollar sign and curly braces to our regex: `r'^[a-zA-Z0-9\.\-\$_,\{\}]+$'`

// TODO - add health check info

https://quarkus.pro/guides/kafka-streams.html#quarkus-kafka-streams_quarkus.kafka-streams.topics


### Performance-oriented rules

#### Throughput-friendly caching - `kafka-streams.statestore.cache.max.bytes`

The Quarkus Kafka Streams tutorial recommends setting the value to `10240`. This is good for testing, as records are progressing through the topology quickly. For production, higher values are recommended.

In our setup, we are expecting this value to be either left at the default value of `10485760`, or set to a value over `1000000`.

https://quarkus.io/guides/kafka-streams

#### If explicitly setting producer `linger.ms`, do not use exreme values

The default is `100`, optimized for low latency.
For high throughput, consider increasing the value, accompanied by continuous testing. 
A value between `10` and `200` ms is required in our setup. 

Please identify the value range best suited for your application by tweaking the configuration. 

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#linger-ms

https://github.com/apache/kafka/blob/3.7/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L1182

#### Explicitly set producer `batch.size` for increased throughput 

The default is `16384`, optimized for low latency.
For a higher throughput, consider increasing the value, accompanied by continuous testing. 

If a value is set, it has to be between `32768` and `262144` in our setup. The value can remain unset.

Please identify the value range best suited for your application by tweaking the configuration. 

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#batch-size

#### Adjust consumer `fetch.min.bytes` for throughput

Is `1` by default. The default is fine for low latency and low throughput applications. 
With increasing throughput, you will benefit from the consumer waiting for a little longer to collect more records (up to the max of `fetch.max.wait.ms = 500`), resulting in a lower number of calls to the cluster and overhead for fetch processing.    

On the other hand, a combination of a very low `fetch.min.bytes` and `fetch.max.wait.ms` can lead to a high number of small fetch requests, putting additional load on the cluster.  

In our example, we are setting this configuration to a range betwee `1000` and `10000` bytes.

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#fetch-min-bytes

#### If consumer `fetch.max.wait.ms` is set, do not set it too low

As explained in the rule for `fetch.min.bytes`, a combination of a very low `fetch.min.bytes` and `fetch.max.wait.ms` can lead to a high number of small fetch requests, putting additional load on the client and the cluster.

In our example, we restrict `fetch.max.wait.ms` to a value between `100`and `1000`.

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#fetch-max-wait-ms


## TODO





### Set producer `delivery.timeout.ms` 

Defaults to 120000 - 2 minutes. Recommended to set to Integer.MAX_VALUE


### Set producer `max.block.ms` to Integer.MAX_VALUE

#### Required for correctness in Apache Kafka clients prior to 2.6

client.dns.lookup=use_all_dns_ips

#### Best practice for higher availability in Apache Kafka clients prior to 3.0

session.timeout.ms=45000


#### Cloud provider-specific disconnect times with `connections.max.idle.ms`

AWS 350 seconds, Azure 4 minutes, Google Cloud 10 minutes.

Default - 540000 ms (9 min)

https://docs.confluent.io/cloud/current/client-apps/client-configs.html

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#connections-max-idle-ms

### Do not set `retries`, or se them to Integer.MAX_VALUE

https://github.com/confluentinc/kafka/blob/v7.6.1/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L703


https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#retries

### Default error handling

In our example, we require that the deserialization handler is either not set, or expects a hypothetical error handler class.

Deserialization error handling in Kafka Streams aims to prevent data loss by failing on error. 

Your application might need a different strategy, e.g. log and continue, or even write to a DLT.  


## Testing the rules

You can test the rules on your properties file:

`python ./scripts/validate_properties.py <path_to_properies_file>`

If no path is provided as an argument, the default `src/main/resources.properties` will be used. 


## TODOs

* profile-specific rules

