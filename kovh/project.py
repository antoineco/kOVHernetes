from .utils import columns


def get_flavors(client):
    flavors = []
    headers = ['ID', 'NAME', 'VCPUS', 'RAM', 'DISK', 'TYPE', 'REGION']

    params = {}
    if client._region:
        params['region'] = client._region

    for fl in client.get('/cloud/project/{}/flavor'.format(client._project), **params):
        if fl['name'][:4] != 'win-':
            flavors.append(
                (
                    fl['id'],
                    fl['name'],
                    str(fl['vcpus']),
                    str(fl['ram']),
                    str(fl['disk']),
                    fl['type'],
                    fl['region']
                )
            )

    return columns(headers, flavors)

def get_images(client):
    images = []
    headers = ['ID', 'NAME', 'USER', 'REGION']

    params = { 'osType': 'linux' }
    if client._region:
        params['region'] = client._region

    for img in client.get('/cloud/project/{}/image'.format(client._project), **params):
        images.append(
            (
                img['id'],
                img['name'],
                img['user'],
                img['region']
            )
        )

    return columns(headers, images)

def get_instances(client):
    instances = []
    headers = ['ID', 'NAME', 'STATUS', 'REGION', 'IP']

    for inst in client.get('/cloud/project/{}/instance'.format(client._project)):
        ip_addrs = []
        for ip in inst['ipAddresses']:
            if ip['version'] == 4:
                ip_addrs.append(ip['ip'])

        instances.append(
            (
                inst['id'],
                inst['name'],
                inst['status'],
                inst['region'],
                ','.join(ip_addrs)
            )
        )

    return columns(headers, instances)

def get_keys(client):
    keys = []
    headers = ['ID', 'NAME']

    for key in client.get('/cloud/project/{}/sshkey'.format(client._project)):
        keys.append(
            (
                key['id'],
                key['name']
            )
        )

    return columns(headers, keys)

def get_networks(client):
    networks = []
    headers = ['ID', 'NAME', 'VLAN', 'STATUS']

    for net in client.get('/cloud/project/{}/network/private'.format(client._project)):
        networks.append(
            (
                net['id'],
                net['name'],
                net['vlanId'],
                net['status']
            )
        )

    return columns(headers, networks)

def get_regions(client):
    regions = []
    headers = ['NAME', 'CONTINENT']

    region_names = client.get('/cloud/project/{}/region'.format(client._project))
    for r_name in region_names:
        r_cont = client.get('/cloud/project/{}/region/{}'.format(client._project, r_name))['continentCode']
        regions.append(
            (
                r_name,
                r_cont
            )
        )

    return columns(headers, regions)

def get_services(client):
    services = []
    headers = ['ID', 'DESCRIPTION']

    service_ids = client.get('/cloud/project')
    for s_id in service_ids:
        s_desc = client.get('/cloud/project/{}'.format(s_id))['description']
        services.append(
            (
                s_id,
                s_desc if s_desc is not None else ''
            )
        )

    return columns(headers, services)

def get_snapshots(client):
    snapshots = []
    headers = ['ID', 'NAME', 'USER', 'REGION']

    params = {}
    if client._region:
        params['region'] = client._region

    for snap in client.get('/cloud/project/{}/snapshot'.format(client._project), **params):
        snapshots.append(
            (
                snap['id'],
                snap['name'],
                snap['user'],
                snap['region']
            )
        )

    return columns(headers, snapshots)

def get_usage(client):
    usage = []
    headers = ['RESOURCE', 'COST', 'TYPE']

    type_field = {
        'instance': 'reference',
        'storage': 'type',
        'volume': 'type'
    }

    u_hourly = client.get('/cloud/project/{}/usage/current'.format(client._project))['hourlyUsage']
    if u_hourly is not None:
        for _type, costs in u_hourly.items():
            for cost in costs:
                #usage.append((_type, cost))
                usage.append(
                    (
                        _type,
                        '€{}'.format(cost['totalPrice']),
                        cost.get(type_field.get(_type), '')
                    )
                )

    return columns(headers, usage)

def get_coreos_images(client):
    imgs = []

    params = {
        'osType': 'linux',
        'region': client._region
    }

    # TODO: revisit once OVH updates its image
    #for img in client.get('/cloud/project/{}/image'.format(client._project), **params):
    #    if 'CoreOS' in img['name']:
    #        imgs.append(img['id'])
    for img in client.get('/cloud/project/{}/snapshot'.format(client._project), **params):
        if 'Container Linux' in img['name']:
            imgs.append(img['id'])

    return imgs

def get_public_networks(client):
    networks = []

    for net in client.get('/cloud/project/{}/network/public'.format(client._project)):
        networks.append(net['id'])

    return networks
