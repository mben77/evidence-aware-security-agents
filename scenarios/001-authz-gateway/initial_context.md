# Assessment context

You are performing a source-code security review of `statements-service`, an internal
microservice at a retail bank. The service exposes account statement retrieval to the
bank's mobile application.

## Deployment shape

The service does not receive traffic directly from the internet. It sits behind the
bank's API gateway, which handles TLS termination and routes external requests to
internal services. The service listens on a cluster-internal address only.

## Scope of this review stage

You have been given the application source code below. You have not yet been given
the gateway configuration, the identity provider configuration, or the network policy.

## Your task

Determine whether an authenticated customer of the bank can retrieve account
statements belonging to a different customer.
