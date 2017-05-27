# Commands reference

Get help about any command by passing the `-h` flag to it.

#### `auth`

Interact with the OVH authentication API.

```
Usage: auth <command>

Commands:
  renew   Request a new consumer key
  show    Display information about current OVH credential
```

#### `project`

Get information about cloud projects.

```
Usage: project <command>

Commands:
  flavors     List available instance flavors for active project
  images      List available OS images for active project
  instances   List existing instances in active project
  keys        List available SSH keys for active project
  networks    List existing networks in active project
  regions     List available regions for active project
  services    List all OVH cloud projects (services)
  snapshots   List available snapshots for active project
  show        Display active project configuration
  usage       Show costs of active project for the current month
```

#### `create`

Create a Kubernetes cluster.

```
Usage: create -n NAME

Options:
  -n, --name NAME   Cluster name
```

#### `destroy`

Destroy a Kubernetes cluster.

```
Usage: destroy -n NAME

Options:
  -n, --name NAME   Cluster name
```
