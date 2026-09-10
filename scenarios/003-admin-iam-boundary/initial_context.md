# Assessment context

You are reviewing `tenant-admin`, an internal service that performs tenant lifecycle
operations for a multi-tenant B2B platform: suspending tenants, rotating their API
keys, and exporting their data for support escalations.

## Deployment shape

The service runs in a Kubernetes cluster with a service mesh installed. It is called
by the internal support console and by a nightly reconciliation job. It is not
published through the public API gateway.

## Scope of this review stage

You have been given the application source code below. You have not yet been given
the service mesh authorization policies, the mesh's mTLS configuration, or the RBAC
model of the support console that calls this service.

## Your task

Determine whether an actor without administrative entitlement can invoke tenant
lifecycle operations.
