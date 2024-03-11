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

When working with Conflunet Cloud, the value for the security protocol always needs to be set to `SASL_SSL`. 

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

For correct functionality

## TODOs

* profile-specific rules


