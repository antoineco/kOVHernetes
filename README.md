# kOVHernetes

![kOVHernetes][logo]

kOVHernetes (*`kovh`*) is a command-line tool for managing Kubernetes clusters on the [OVH Cloud][ovhcloud] platform.

It creates Kubernetes clusters based on the CoreOS [Container Linux][cont-linux] operating system with
[flannel][flannel] providing the virtual container network.

#### Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Disclaimer](#disclaimer)
6. [Roadmap](#roadmap)

## Prerequisites

### :warning: CoreOS Container Linux image

The *Container Linux* image available in the OVH image service as of 05/19/2017 is outdated and therefore missing
features required by the `kovh` client (Ignition OpenStack compatibility, *rkt* wrapper scripts).

Until this problem is tackled by OVH, please follow the instructions at [Running CoreOS Container Linux on
OpenStack][coreos-openstack] to download the latest Stable release, then upload it to your OVH account with:

```sh
❯ openstack image create \
    --disk-format 'qcow2' \
    --file 'coreos_production_openstack_image.img' \
    --property os-distro='container' \
    --property os-version='1353.7.0' \
    --property image_original_user='core' \
    'Container Linux Stable'
```

[coreos-openstack]: https://coreos.com/os/docs/latest/booting-on-openstack.html

### Runtime

[Python][python] interpreter (version 3.2 or above) with the [`setuptools`][setuptools] package.

### Cloud provider

* At least one Cloud project must be created before resources can be provisioned by kOVHernetes.
* The Cloud project must be associated with a vRack in order to create Private Networks.
* At least one SSH public key must have been added to the project.

![OVH dashboard][dash]

## Installation

Run the following command inside the repository to install the project dependencies and the `kovh` executable:

```sh
❯ python setup.py install
```

## Configuration

### .conf files

The CLI configuration is read from the following files (in this order):

* `kovh.conf` (current directory)
* `ovh.conf` (current directory)
* `~/.ovh.conf` (home directory)
* `/etc/ovh.conf` (system-wide)

Copy the sample `kovh.conf.example` file to one of these locations and edit it with the following settings:

1. `application_key`, `application_secret`

*Application* kOVHernetes uses to interact with the API. Requested once at https://api.ovh.com/createApp/. The
application is tied to your personal account and accepts any name/description.

2. `consumer_key`

Grants API access to the *Application*. Obtained using the following command after adding the previous information:

```sh
❯ kovh auth renew
```

3. `project`, `sshkey`, `region`, `flavor`

*Project (service)*, *SSH key*, *region* and *flavor (instance type)* IDs. Obtained using the following commands
respectively:

```sh
❯ kovh project services
❯ kovh project keys
❯ kovh project regions
❯ kovh project flavors
```

### Environment variables

Alternatively, all settings can be overriden by environment variables using the format `OVH_<uppercase:setting>`.

```sh
# example
❯ export OVH_PROJECT=6f39672f2931ed50922041972b355ab8
❯ kovh project instances
```

## Usage

* [Command reference][cmd-ref]

[cmd-ref]: docs/commands-reference.md

## Disclaimer

**Use at your own risk**.

* This project is **not** supported by [OVH][ovh] in any way.
* This is a toy project for testing purposes. Several security aspects have been omitted for the sake of simplicity.

## Roadmap

* [ ] Clusters listing
* [ ] `kubectl` configuration
* [ ] Multi-node clusters
* [ ] PKI
* [ ] CNI networking


[logo]: images/logo.png
[ovhcloud]: https://www.ovh.com/cloud/
[cont-linux]: https://coreos.com/os/
[flannel]: https://coreos.com/flannel/
[python]: https://www.python.org/downloads/
[setuptools]: https://pypi.python.org/pypi/setuptools
[dash]: images/project_dashboard.png
[ovh]: https://www.ovh.com/
