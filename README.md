# quarkusconfigrules

The purpose of this project is to provide enforceable guidelines on application configurations. 
In this first iteration, specifically on Kafka Streams applications created with the Quarkus framework. 

The assumption is that the configuration is contained in the `src/resources/application.properties` file. 

## Configuration and selection

In Apache Kafka 2.8, there are ~100 configurations that can be set for Kafka Producers and ~200+ configurations for Kafka Consumers. Furthermore, there is a bunch of Kafka Streams-specific configurations, some of them implicitly influencing the underlying client settings.   

Thankfully, the majority of these configurations have sensible defaults, and don’t need to be adjusted for most workloads. Configurations are continuously reviewed by Confluent and the Apache Kafka community, and the default values are adjusted based on feedback and common issues experienced by developers. For example, some of the more impactful changes were introduced with Apache Kafka 3.0.x & 3.1, changing the producer defaults for `acks` and `enable.idempotence` to more robust defaults. However, changing the defaults is a long process, it requires upgrading the clients, and some defaults still might not fit all use cases.  

The focus of this selection of configurations was to make our Quarkus-based Kafka Streams applications more robust. Sometimes this means enforcing what is already the default, as not all applications are using the newest client versions. Some rules rather provide guidance and are intended to be changed by the application team.

We tried to provide explanations and references for every rule. Surely, many of these explanations and references can be improved and extended. Feel free to do so and let us know. 

## Rules

There are several types of rules: 

* Some enforce a value or one of many possible values, a value range or a regex match. 
* Some enforce a reasonable cooperation of values.  
* Some enforce that once a default value has been overridden, it is done on purpose, and with a reasonable alternative. 
* And some others, which do not fit in any of the above groups. 

Let's look into the options in more detail.

### Enforcing a value or value range

* Single value 

When working with Confluent Cloud, the value for the security protocol always needs to be set to `SASL_SSL`. Anything else will lead to errors.

* One value of many 

When deciding on one of many options, e.g. compression algorithm, the decision depends on the data and should be the result of benchmarking. 
As an example, w‚e might decide to allow `snappy` and `lz4`, while disallowing `gzip` and `zstd`.

* Value range

We might decide to override `max.poll.records`, to reduce or increase the number of records processed per poll loop. These changes need to be restricted in a reasonable range.

* Value regular expression

Some values, such as topic names can only be checked for plausibility, not for their concrete values. For this purpose, regex matching validations are used. 

### Enforcing property combinations

* Value as a range of multiples of another value

Consumer configuration:

`default.api.timeout.ms` defaults to 60 seconds.

`request.timeout.ms` defaults to 30 seconds.

Some applications override/increase the request timeout, in order to be able to handle longer outages. However, they might forget to also increase the default API timeout.   

The default API timeout value should be greater than the request timeout in order to be able to gracefully handle errors, e.g. committing offsets in an exception handler. If this is not the case, the application will timeout immediately, after the request timeout threshold has been reached. 

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#request-timeout-ms

* Only one of multiple properties can be set

Quarkus offers multiple ways of setting the same parameters. Either one of those can be used. Using multiple properties in the same file may lead to unnecessary confusion. 

* Conditional numeric range

Some properties imply changes in others properties. For example, enabling exactly-once processing implicitly changes commit intervals and further producer properties.

This type of rule enforces an value range of one property, but only if a different property has been set to a certain value.  

### Other rules

* Making sure a property is NOT set

This is useful to prevent applications from using deprecated properties, which will be removed in the future, or prevent reasonable defaults from being overridden.  

### Defaults are fine, overrides need to be coordinated

The default deserialization exception handler will fail on a message it cannot read, bringing down the instance. In many cases, this is the desired behavior. However, we might want to rather skip the record and continue.

This decision needs to be communicated and agreed upon, so by default, overriding the handler is not allowed. The rule can be disabled for a project, once consensus has been reached.

### Implementation and application

The validations are implemented in a generic way, to be applied to multiple existing rules, as well as potential further rules in the future.  

The implementation of generic rules can be found in the `scripts/validations.py` file.

The configuration of specific rules can be found in the `scripts/validate_properties.py` file. 

## Details

### Error aggregation

While we value rapid feedback, complete feedback is even more preferable. We do not fail on the first rule violation. We aggregate all violations, so they can be reviewed and fixed all at once, saving precious cycle time. 

### Profiles and prefixes

The Quarkus framework offers the possibility to work with multiple profiles. In the configuration files, the properties are then prefixed with the profile name, e.g. 

`%prod.kafka.sasl.mechanism=PLAIN`

For correct functionality, we need to check the configurations ending in the expected string.  

The rules allow for ignoring any violations in certain profiles. By default, properties in the `dev` and `test` profiles are not checked for violations. This can be changed per individual rule check.

## The rules

We have organized the rules into groups, each of the groups addressing different aspects of the clients functionality. 

### Increased client stability, resilience, availability

Some rules are difficult to put into a single bucket, as many rules aim on reducing the number of requests and making individual requests more efficient. This can have a positive impact on the throughput of the application, but at the same time reduces the burden on the cluster, by reducing the total amount of requests.

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
Deciding between the remaining three is often a matter of experimentation, as they perform differently depending on multiple factors. 

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

Having this property set to a low value can generate an excessive number of metadata requests, increasing teh load on the client itself and the cluster. 

https://quarkus.io/guides/kafka-streams

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#metadata-max-age-ms

#### Do not configure producer idempotence explicitly, or set it to `true`.

The default for `enable.idempotence` is `true` since AK 3.1. When using older clients, setting it to `true` is recommended.

When using EOS, producer idempotence is enabled by default.

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#enable-idempotence


### Confluent Cloud requirements

#### Set `kafka.security.protocol` to `SASL_SSL`

This is the requirement for Confluent Cloud applications. 

If not set, client might attempt connecting to the cluster using a plaintext protocol, failing the SSL handshake and retrying, effectively trying to DoS the cluster.  

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#security-protocol

#### Set `kafka.sasl.mechanism` to `PLAIN`

This configuration is required by Confluent Cloud.

https://developer.confluent.io/get-started/java/#configuration

#### Use the `PlainLoginModule` in your SASL JAAS config

This configuration is required by Confluent Cloud. We perform a simple regex check for plausibility.

https://developer.confluent.io/get-started/java/#configuration


### Kafka Streams requirements

#### Ensuring `quarkus.kafka-streams.application-id`is set

This configuration is required for the application to start.

The application ID can be a combination of alphanumerics, underscore, dot and dash. We use this regex to ensure this: `r'^[a-zA-Z0-9\.\-_]+$'` . Additional checks can be added to enforce naming and versioning rules. 

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#application-id

#### Ensuring either `kafka-streams.bootstrap-servers` or `kafka.bootstrap.servers`, but not both, is set

This configuration is required for the application to start. The `kafka` variant is used for non-KStreams implementations (e.g. Smallrye Kafka Connector) and is a fallback to the `kafka-streams` variant with Kafka Streams. 

https://quarkus.pro/guides/kafka-streams.html#quarkus-kafka-streams_quarkus.kafka-streams.bootstrap-servers


### Quarkus-specific recommendations

#### Ensuring `quarkus.kafka-streams.topics` is set to a plausible string

Quarkus offers a safeguard, which prevents the Kafka Streams application from starting, unless the configured topics exist on the cluster. 

This configuration is beneficial, so we are requiring it to be set to a non-empty, plausible string.  

Kafka topic names are restricted to alphanumerics, underscore, dot and dash. Since there can be multiple topics, we add the comma, the dollar sign and curly braces to our regex: `r'^[a-zA-Z0-9\.\-\$_,\{\}]+$'`

This validation, though optional, can add useful information on the current state of the application on both liveness and readiness health checks: 

`curl -i http://myapplication:8080/q/health/ready`

```json
{
    "status": "DOWN",
    "checks": [
        {
            "name": "Kafka Streams topics health check",
            "status": "DOWN",
            "data": {
                "missing_topics": "weather-stations,temperature-values"
            }
        }
    ]
}
```

https://quarkus.pro/guides/kafka-streams.html#quarkus-kafka-streams_quarkus.kafka-streams.topics

https://quarkus.io/guides/kafka-streams#kafka-streams-health-checks


### Performance-oriented rules

#### Throughput-friendly caching - `kafka-streams.statestore.cache.max.bytes`

The Quarkus Kafka Streams tutorial recommends setting the value to `10240`. This is good for testing, as records are progressing through the topology quickly. For production, higher values are recommended.

In our setup, we are expecting this value to be either left at the default value of `10485760`, or set to a value over `1000000`.

https://quarkus.io/guides/kafka-streams

#### If explicitly setting producer `linger.ms`, do not use extreme values

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


### Further recommendations

#### Enabling state store and other metrics with `kafka-streams.metrics.recording.level=DEBUG`

The default metrics level is `INFO`. Some important metrics are only collected if `DEBUG` level is activated, e.g. most task-level, state store, and record cache metrics.

https://docs.confluent.io/platform/current/streams/monitoring.html

#### Do not use the deprecated `cache.max.bytes.buffering` and `buffered.records.per.partition` configuration

The configuration has been renamed and is deprecated. However, many parts of the existing documentation did not catch up with the change yet. 

In the same change, the per-partition configuration `buffered.records.per.partition` (defaults to `10000`) was changed to the per-topology `input.buffer.max.bytes` (defaults to `512MB`). We do not have a recommmendation on this new configuration yet. 

The implementation is to be completed with the AK 3.8 release.

KIP-770: https://cwiki.apache.org/confluence/pages/viewpage.action?pageId=186878390
https://issues.apache.org/jira/browse/KAFKA-13152

https://quarkus.io/guides/kafka-streams

#### Do not set `retries`, or set to `Integer.MAX_VALUE (2147483647)`

This configuration is deprecated in Kafka Streams versions 2.8. Embedded clients in Kafka Streams use `Integer.MAX_VALUE` as default. The default value of `retries=0` only applies to the global thread. But if you change the configuration, you may accidentally reduce the producer and admin client retry config. If looking to control the retry timeout boundaries, consider using the new configuration `task.timeout.ms` as an upper bound for any task to make progress with a default config of 5 minutes.

https://github.com/confluentinc/kafka/blob/v7.6.1/streams/src/main/java/org/apache/kafka/streams/StreamsConfig.java#L703

https://cwiki.apache.org/confluence/display/KAFKA/KIP-572%3A+Improve+timeouts+and+retries+in+Kafka+Streams

### Client DNS lookup - use all DNS IPs

The configuration `client.dns.lookup=use_all_dns_ips` is required for correctness in Apache Kafka clients prior to 2.6.

For clients using Kafka Streams version 2.6 and younger, this is already the default. Since we are not checking the client version, we insist on setting the configuration explicitly. 

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#client-dns-lookup

https://cwiki.apache.org/confluence/display/KAFKA/KIP-302+-+Enable+Kafka+clients+to+use+all+DNS+resolved+IP+addresses

https://cwiki.apache.org/confluence/display/KAFKA/KIP-602%3A+Change+default+value+for+client.dns.lookup

#### Consumer session timeout and heartbeat - leave at default or increase reasonably

Kafka consumers send periodic heartbeats to the consumer coordinator to let it know, that they are still alive and are successfully processing messages from their assigned partitions. The heartbeat is generated by a separate thread, so event processing does not interfere with the heartbeat. 

If a consumer stops sending heartbeats for a period of time that exceeds the `session.timeout.ms` setting, its session will expire and the group coordinator will consider the consumer to be dead.

This will trigger a rebalance of the consumer group, in which the partitions previously assigned to the dead consumer are reallocated to the remaining consumers in the group. 

The frequency of the heartbeats is controlled by the `heartbeat.interval.ms` setting, which is set to 3 seconds by default.
The `session.timeout.ms` is set to 45 seconds by default in Kafka versions 3.0 and above, and to 10 seconds in earlier versions.

Leaving both configurations on default values is considered fine. When changing either of the configuration, please be mindful to not set the heartbeat interval to a low value to avoid putting additional load on the consumer coordinator. In our example, we limit the heartbeat interval to values between 3 and 30 seconds. We further limit the heartbeat interval to not be longer than 1/3 of the session timeout to give multiple heartbeat attempts the chance to reach the coordinator.  In our case, we limit the session timeout to values between 30 seconds and 5 minutes. 
 
Please be mindful that in the case of static group membership, the consumer group relies on the session timeout to detect dead clients and perform a rebalance.

https://cwiki.apache.org/confluence/display/KAFKA/KIP-735%3A+Increase+default+consumer+session+timeout

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#heartbeat-interval-ms

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#session-timeout-ms

#### Set producer `delivery.timeout.ms` to `Integer.MAX_VALUE`

`kafka-streams.producer.delivery.timeout.ms`

If the producer times out, the production of the relevant record will not be re-attempted, as Kafka Streams does not store the record and relies on the producer for retries.

Recommended to set to `Integer.MAX_VALUE`, to enable the application to survive cluster outages for longer than the default timeout of 2 minutes. 

#### Set consumer & admin client `default.api.timeout.ms` to 3 to 10 minutes

The default is 1 minute. We want to increase this timeout to give the client the capability to survive longer cluster rolls and similar interruptions.

https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html#default-api-timeout-ms

#### When increasing `request.timeout.ms`, also increase the `default.api.timeout.ms`

Some applications override/increase the request timeout, in order to be able to handle longer outages. However, they might forget to also increase the default API timeout.

The default API timeout value should be greater than the request timeout in order to be able to gracefully handle errors, e.g. committing offsets in an exception handler. If this is not the case, the application will timeout immediately, after the request timeout threshold has been reached. 

`request.timeout.ms` defaults to 30 seconds.

https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#request-timeout-ms


#### Cloud provider-specific disconnect times with `connections.max.idle.ms`

The default value for this configuration is  540000 (9 minutes). Previously, this may have led to issues, as the default idle timeouts on cloud load balancers, sued by Confluent Cloud, were shorter in some cases (AWS - 350 seconds, Azure - 4 minutes, Google Cloud - 10 minutes). Confluent Cloud brokers now terminate idle connections before load balancers do.

In our case, while no longer necessary, we recommend setting the idle connection timeout to a value between 120000 (2 minutes) and 240000 (4 minutes).

https://docs.confluent.io/cloud/current/client-apps/client-configs.html#common-properties

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#connections-max-idle-ms

https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-tcp-reset#configurable-tcp-idle-timeout

#### Default error handling

The default behavior will not lose/skip any data, while the alternative one will skip records in order not to fail and stop the processing.  

Your application might need a different strategy, e.g. log and continue, or write to a DLT. It can thus make sense to replace the default handler for your project, but this decision needs to be documented, among other things in the configuration rules.  

There are two built-in implementations of the `default.deserialization.exception.handler`. The default one (`LogAndFailExceptionHandler`) returns `FAIL` on deserialization exceptions. The `LogAndContinueExceptionHandler` will not fail, but will drop the offending record and continue. 

In our example, we require that the deserialization handler is either not set, or set to to either the default value of `kafka.streams.errors.LogAndFailDeserializationHandler`, or a hypothetical `com.example.CustomDeserializationExceptionHandler` error handler class.

There is just one built-in implementation of the `default.production.exception.handler`, which always fails of non-retriable errors, e.g. `RecordTooLargeException`. By default, we disallow setting this configuration.

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#default-deserialization-exception-handler

https://docs.confluent.io/platform/current/streams/faq.html#streams-faq-failure-handling-deserialization-errors

https://docs.confluent.io/platform/current/streams/developer-guide/config-streams.html#default-production-exception-handler

https://docs.confluent.io/platform/7.6/streams/javadocs/javadoc/org/apache/kafka/streams/errors/DefaultProductionExceptionHandler.html


## Testing the rules

You can test the rules on your properties file:

`python ./scripts/validate_properties.py <path_to_properies_file>`

If no path is provided as an argument, the default `src/main/resources.properties` will be used. 


## TODOs

* profile-specific rules

