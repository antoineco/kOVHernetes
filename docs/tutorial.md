# Tutorial

This is a good place to start if you want to understand the basics of the `kovh` utility and make sure your Kubernetes
clusters are working as intended. It also describes some very basic Kubernetes concepts in order to get you started.

*This tutorial assumes that a project is already configured as described in the README*

#### Contents

1. [Spin-up a cluster](#spin-up-a-cluster)
2. [Look around](#look-around)
3. [Navigate your cluster](#navigate-your-cluster)
4. [Tear down the cluster](#tear-down-the-cluster)

## Spin-up a cluster

The `create` command is used to deploy a new cluster inside an OVH Cloud project. The only information you have to
provide is a unique name for that cluster. I named mine `cursedfleet` for this example. You can optionally provide a
cluster size as well. The default is **3**.

```
❯ kovh create --name cursedfleet --size 3

Creating private network 'kovh:cursedfleet:' with VLAN id 0	[OK]
Waiting for readiness of private network 'kovh:cursedfleet:'..	[OK]
Creating subnet	[OK]
Creating Certificate Authority	[OK]
Creating instances	[OK]
```

*What just happened?*

1. A private network was created in the project's vRack with the next available VLAN id
2. The subnet 192.168.0.0/24 was created within this private network, in the configured region
3. A Certificate Authority was generated locally and in memory, it will enable PKI authentication within the cluster
4. The creation of 3 new instances was initiated

You can see the instances being created using the `project instances` subcommand.

```
❯ kovh project instances

ID                                    NAME                      STATUS  REGION  IP                         
ccdf2160-6481-4262-b4d1-4d73574d96c5  kovh:cursedfleet::node02  BUILD   GRA3    147.135.193.252,192.168.0.4
2299a23e-e116-4380-af49-0fa91e9170dc  kovh:cursedfleet::node01  BUILD   GRA3    147.135.193.25,192.168.0.3 
17c23e1f-4c1c-4dd2-a2a8-f7cd9871eb0a  kovh:cursedfleet::master  ACTIVE  GRA3    147.135.193.248,192.168.0.1
```

A few things should be noted before jumping to the next steps:

* The `master` instance runs the "master" Kubernetes components (api, scheduler, controller manager) including an
instance of the [etcd][etcd] key-value store, together with the "node" Kubernetes components (kubelet, proxy). As
deployed with kOVHernetes, the `master` instance is effectively both the cluster master **and** a worker node.
* The `node*` instances run only the "node" Kubernetes components (kubelet, proxy).

## Look around

Shortly after an instance becomes *ACTIVE*, you should be able to connect to it over SSH as the `core` user using the
SSH key configured in your project. Let's start by logging in to the `master` instance:

```
❯ ssh core@147.135.193.248

Container Linux by CoreOS stable (1353.7.0)
core@host-192-168-0-1 ~ $
```

The following critical services should be in the process of starting, or already started:

* `kubelet.service`: starts all other Kubernetes components as [Pods][pod].
* `etcd-member.service`: provides configuration persistence to the Kubernetes API server.
* `flanneld.service`: creates the overlay network used for inter-container communications.

Ensure all 3 services started without errors with:

```
core@host-192-168-0-1 ~ $ systemctl status kubelet etcd-member flanneld

● kubelet.service - Kubernetes kubelet (System Application Container)
   Loaded: loaded (/etc/systemd/system/kubelet.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2017-05-31 11:48:24 UTC; 7min ago
   [...]

● etcd-member.service - etcd (System Application Container)
   Loaded: loaded (/usr/lib/systemd/system/etcd-member.service; enabled; vendor preset: enabled)
  Drop-In: /etc/systemd/system/etcd-member.service.d
           └─10-cluster.conf
   Active: active (running) since Wed 2017-05-31 11:48:25 UTC; 7min ago
   [...]

● flanneld.service - flannel - Network fabric for containers (System Application Container)
   Loaded: loaded (/usr/lib/systemd/system/flanneld.service; enabled; vendor preset: enabled)
  Drop-In: /etc/systemd/system/flanneld.service.d
           └─10-network-config.conf
   Active: active (running) since Wed 2017-05-31 11:48:46 UTC; 6min ago
   [...]
```

Additionally, you should be able to list the [rkt][rkt] containers running these 3 services (yup, everything is
containerized!).

```
core@host-192-168-0-1 ~ $ rkt list

UUID      APP        IMAGE NAME                                STATE
079c62f6  hyperkube  quay.io/coreos/hyperkube:v1.6.4_coreos.0  running
154b06de  flannel    quay.io/coreos/flannel:v0.7.0             running
cd973167  flannel    quay.io/coreos/flannel:v0.7.0             exited
d704531f  etcd       quay.io/coreos/etcd:v3.0.10               running
```

The `kubelet` component should have started all pods described within the `/etc/kubernetes/manifests` directory:

* *kube-addon-manager.yml*
* *kube-apiserver.yml*
* *kube-controller-manager.yml*
* *kube-proxy.yml*
* *kube-scheduler.yml*

These pods are backed by Docker, so you should be able to list them as well:

```
core@host-192-168-0-1 ~ $ docker ps

CONTAINER ID   IMAGE                         COMMAND                  NAMES
fe5d87cf1ed7   quay.io/coreos/hyperkube@...  "kube-controller-mana"   k8s_kube-controller-manager_...
f55519a32588   quay.io/coreos/hyperkube@...  "kube-scheduler --kub"   k8s_kube-scheduler_kube-sche...
1f2a6d6bcb9f   quay.io/coreos/hyperkube@...  "kube-proxy --kubecon"   k8s_kube-proxy_kube-proxy-ho...
cfb8da05a434   quay.io/coreos/hyperkube@...  "kube-apiserver --etc"   k8s_kube-apiserver_kube-apis...
05a65d77be0a   gcr.io/kube-addon-manager...  "/opt/kube-addons.sh"    k8s_kube-addon-manager_kube-...
58a47536bd81   gcr.io/pause-amd64:3.0        "/pause"                 k8s_POD_kube-scheduler-host-...
6d461fc4aeab   gcr.io/pause-amd64:3.0        "/pause"                 k8s_POD_kube-apiserver-host-...
262ecfb753de   gcr.io/pause-amd64:3.0        "/pause"                 k8s_POD_kube-controller-mana...
e34ad19e4795   gcr.io/pause-amd64:3.0        "/pause"                 k8s_POD_kube-proxy-host-192-...
953b9e8c0250   gcr.io/pause-amd64:3.0        "/pause"                 k8s_POD_kube-addon-manager-h...
```

One of these containers is the `kube-apiserver`, which means from this point forward you should be able to interact with
your Kubernetes cluster using the pre-installed `kubectl` utility.

## Navigate your cluster

Your cluster is composed of **3** nodes, one being the master you're currently connected to. All 3 should already be
registered with the API server.

```
core@host-192-168-0-1 ~ $ kubectl get nodes

NAME               STATUS   AGE   VERSION
host-192-168-0-1   Ready    8m    v1.6.4+coreos.0
host-192-168-0-3   Ready    8m    v1.6.4+coreos.0
host-192-168-0-4   Ready    8m    v1.6.4+coreos.0
```

It has some default [Namespaces][namespace] pre-created.

```
core@host-192-168-0-1 ~ $ kubectl get namespaces

NAME          STATUS    AGE
default       Active    8m
kube-public   Active    8m
kube-system   Active    8m
```

One of these namespaces is `kube-system`. By convention it contains all the pods necessary to the cluster operations, as
well as the cluster addons.

```
core@host-192-168-0-1 ~ $ kubectl -n kube-system get pods

NAME                                       READY     STATUS    RESTARTS   AGE
kube-addon-manager-host-192-168-0-1        1/1       Running   0          6m
kube-apiserver-host-192-168-0-1            1/1       Running   0          7m
kube-controller-manager-host-192-168-0-1   1/1       Running   0          6m
kube-dns-806549836-bc2l4                   3/3       Running   0          7m
kube-proxy-host-192-168-0-1                1/1       Running   0          6m
kube-proxy-host-192-168-0-3                1/1       Running   0          6m
kube-proxy-host-192-168-0-4                1/1       Running   0          7m
kube-scheduler-host-192-168-0-1            1/1       Running   0          6m
kubernetes-dashboard-2917854236-wkpv6      1/1       Running   0          7m
```

Did you notice the name of these pods? They correspond exactly to the output of the `docker ps` command executed in the
previous section.

Now go ahead and create a replicated application. [`nginx`][nginx-hub] is often used as a quickstart example. Ours will
have 5 replicas.

```
core@host-192-168-0-1 ~ $ kubectl run nginx --image=nginx --replicas=5

deployment "nginx" created
```

You did not explicitely define any namespace on the command line, so all resources were created within the `default`
namespace.

```
core@host-192-168-0-1 ~ $ kubectl get pods

NAME                     READY     STATUS    RESTARTS   AGE
nginx-2371676037-b04l0   1/1       Running   0          1m
nginx-2371676037-ftnsj   1/1       Running   0          1m
nginx-2371676037-kbl3s   1/1       Running   0          1m
nginx-2371676037-p1j5v   1/1       Running   0          1m
nginx-2371676037-xrvdh   1/1       Running   0          1m
```

In Kubernetes, the lifecycle of a group of pods is usually controlled by a [Deployment][deployment] controller under the
hood.

```
core@host-192-168-0-1 ~ $ kubectl get deployments

NAME      DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
nginx     5         5         5            5           1m
```

Such controller ensures that all replicas (pods) are running, healthy, and in the described state. If you try to break
the defined state by, for example, deleting a pod, the controller will recreate another replica immediatly in order to
match the desired state.

```
core@host-192-168-0-1 ~ $ kubectl delete pod nginx-2371676037-b04l0

pod "nginx-2371676037-b04l0" deleted
```
```
core@host-192-168-0-1 ~ $ kubectl get pods

NAME                     READY     STATUS        RESTARTS   AGE
nginx-2371676037-762rg   1/1       Running       0          12s
nginx-2371676037-b04l0   0/1       Terminating   0          4m
nginx-2371676037-ftnsj   1/1       Running       0          4m
nginx-2371676037-kbl3s   1/1       Running       0          4m
nginx-2371676037-p1j5v   1/1       Running       0          4m
nginx-2371676037-xrvdh   1/1       Running       0          4m
```

Two interesting things to notice here:

* I requested the deletion of the pod `nginx-2371676037-b04l0`, which transitioned to the *Terminating* state
* It was replaced right away by another identical pod, `nginx-2371676037-762rgI`

Passing the `-o wide` flag to the previous command will show you the **internal** IP address of each of your pod, and
the node it's running on.

```
core@host-192-168-0-1 ~ $ kubectl get pods -o wide

NAME                     READY   STATUS    RESTARTS   AGE   IP            NODE
nginx-2371676037-762rg   1/1     Running   0          5m    172.17.29.3   host-192-168-0-4
[...]
```

Since our `nginx*` pods are running a web server, you can already send them a HTTP request using `curl` from within the
cluster.

However, how can you expose these pods to the outside world? Simple, create a [Service][service] matching the deployment
created previously.

```
core@host-192-168-0-1 ~ $ kubectl expose deployment nginx --port=80 --target-port=80 --type=NodePort

service "nginx" exposed
```

What we created here is an abstraction providing a unique internal virtual IP to **all** the pods managed by the `nginx`
deployment. The `--port` flag indicates on which port this service should serve (80), the `--target-port` matches the
port [exposed by the containers][dfile-port80], while `--type=NodePort` instructs the `kube-proxy` to expose **the same
random high port** on every cluster node.

[dfile-port80]: https://github.com/nginxinc/docker-nginx/blob/c769ad8ab21dfb374fa33d8fb9d0822d0fa8d2e5/mainline/stretch/Dockerfile#L39

```
core@host-192-168-0-1 ~ $ kubectl get svc nginx

NAME    CLUSTER-IP   EXTERNAL-IP   PORT(S)        AGE
nginx   10.0.0.95    <nodes>       80:30468/TCP   12s
```

The internal IP 10.0.0.95 was assigned to our service. If you send requests to that IP from within your cluster,
`kube-proxy` will distribute them accross all the pods belonging to the `nginx` deployment, in a round-robin fashion.

The high port 30468 was also opened for that same service, so you can now send requests to that port from outside of
your cluster, using any node public IP address.

![nginx request][nginx-highport]

## Tear down the cluster

It's now the end of this tutorial, you can destroy your cluster whenever you're done using it. All you have to do is
pass the cluster name to the `destroy` command.

```
❯ kovh destroy -n cursedfleet

Destroying instance 'kovh:cursedfleet::node02'	[OK]
Destroying instance 'kovh:cursedfleet::node01'	[OK]
Destroying instance 'kovh:cursedfleet::master'	[OK]
Waiting for instances termination...	[OK]
Destroying private network 'kovh:cursedfleet:'	[OK]
```


[etcd]: https://coreos.com/etcd
[pod]: https://kubernetes.io/docs/concepts/workloads/pods/pod/
[namespace]: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
[service]: https://kubernetes.io/docs/concepts/services-networking/service/
[deployment]: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
[rkt]: https://coreos.com/rkt
[nginx-hub]: https://hub.docker.com/_/nginx/
[nginx-highport]: images/nginx_highport.png
