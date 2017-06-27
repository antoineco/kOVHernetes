# Cluster architecture

This page describes some technical aspects of a Kubernetes cluster deployed using kOVHernetes.

#### Contents

1. [Overview](#overview)
2. [Topology](#topology)
3. [Networking](#networking)
4. [Security](#security)

## Overview

![kOVHernetes cluster architecture][kovh-arch]

## Topology

Every cluster is composed of **1** master and a number of nodes (workers) defined on the command line.

* The `master` instance runs the "master" Kubernetes components (api, scheduler, controller manager) including an
instance of the [etcd][etcd] key-value store, together with the "node" Kubernetes components (kubelet, proxy). As
deployed with kOVHernetes, the `master` instance is effectively both the cluster master **and** a worker node.
* The `node*` instances run only the "node" Kubernetes components (kubelet, proxy).

## Networking

3 different networks are involved in a typical Kubernetes cluster.

### Host network

| CIDR           | Description                                                               |
|----------------|---------------------------------------------------------------------------|
| 192.168.0.0/27 | Private network (OVH vRack) to which all cluster instances are connected. |

A reserved and predictable IP address is assigned to each cluster instance duríng the bootstrap process. Each instance
acquires its network configuration from the DHCP server (backed by OpenStack Neutron) at boot time.

### Pod network

| CIDR          | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| 172.17.0.0/16 | Overlay network from which each Kubernetes Pod gets assigned an IP address. |

This network is managed by [flannel][flannel], configured with the [VXLAN][vxlan] backend. A subnet of length /24 gets
allocated to the `flannel.1` vxlan interface on every node from this network.

### Service network

| CIDR        | Description                                                              |
|-------------|--------------------------------------------------------------------------|
| 10.0.0.0/16 | Virtual network from which Kubernetes Services receive their cluster IP. |

The [Kubernetes proxy][kube-proxy] implements the service abstraction using `iptables` on each instance it runs on.

## Security

Security within a cluster is enforced at multiple levels.

### Transport

All inter-components communications within the cluster are made [over a TLS connection][k8s-tls], comprising:

* Kubernetes components <-> Kubernetes API server
* Kubernetes API server <-> etcd
* flannel <-> etcd

The only exception is the Kubernetes API server, which serves an unsecured and unauthenticated access reachable only
from localhost on the TCP port 8080 (master instance).

### Authentication

kOVHernetes generates a Certificate Authority and a set of X.509 certificates during the bootstrap process. These
certificates are used to authenticate client components against server components. The matrix below describes these
interactions:

:key: &nbsp; X.509 auth  
:o: &nbsp; Work in progress

| *Client* / *Server* | kube-api | kubelet | kube-&ast; | etcd  | flannel |
|:-------------------:|:--------:|:-------:|:----------:|:-----:|:-------:|
| **kube-api**        | -        | :o:     |            | :key: |         |
| **kubelet**         | :key:    | -       |            |       |         |
| **kube-&ast;**      | :key:    |         | -          |       |         |
| **etcd**            |          |         |            | -     |         |
| **flannel**         |          |         |            | :key: | -       |

\* *`kube-*` includes `kube-scheduler`, `kube-controller-manager` and `kube-proxy`*

<!-- TODO
https://kubernetes.io/docs/admin/kubelet-authentication-authorization/
-->

### Authorization

#### Kubernetes

The Kubernetes API authorization mode is left to its default of `AlwaysAllow`. In this mode:

* any authenticated user (X.509/token/basic) can perform any action on the API
* anonymous requests are always rejected

After the cluster is provisioned, the API server can be maually configured to enable other authorization plug-ins (RBAC,
ABAC, ...).

#### etcd

While [client certificate authentication][etcd-auth] is enforced for both client and peer communications (see above),
authenticated users are systematically granted full access to the etcd v3 API. The [v3 authorization
mechanism][etcd-v3auth] is still in a design phase upstream.


[kovh-arch]: images/kovh_arch.png
[etcd]: https://coreos.com/etcd
[flannel]: https://coreos.com/flannel
[vxlan]: https://github.com/coreos/flannel/blob/71e526160829fc85af750201b767cfc118292ff1/Documentation/backends.md#vxlan
[kube-proxy]: https://kubernetes.io/docs/concepts/services-networking/service/#proxy-mode-iptables
[k8s-tls]: https://kubernetes.io/docs/admin/accessing-the-api/#transport-security
[k8s-x509]: https://kubernetes.io/docs/admin/authentication/#x509-client-certs
[etcd-auth]: https://coreos.com/etcd/docs/latest/op-guide/security.html#example-2-client-to-server-authentication-with-https-client-certificates
[etcd-v3auth]: https://github.com/coreos/etcd/blob/master/Documentation/learning/auth_design.md
