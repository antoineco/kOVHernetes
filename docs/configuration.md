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
