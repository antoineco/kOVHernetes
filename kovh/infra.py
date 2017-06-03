from ovh import APIError, ResourceNotFoundError


def create_priv_network(client, name, vlan):
    params = {
        'name': name,
        'regions': [client._region],
        'vlanId': vlan
    }

    try:
        net = client.post('/cloud/project/{}/network/private'.format(client._project), **params)
    except APIError:
        raise
    else:
        return net

def create_subnet(client, net_id, subnet):
    hosts = tuple(subnet.hosts())

    params = {
        'networkId': net_id,
        'dhcp': True,
        'noGateway': True,
        'region': client._region,
        'network': str(subnet),
        'start': str(hosts[0]),
        'end': str(hosts[-1])
    }

    try:
        subnet = client.post('/cloud/project/{}/network/private/{}/subnet'.format(client._project, net_id), **params)
    except APIError:
        raise
    else:
        return subnet

def next_vlan(client):
    try:
        networks = client.get('/cloud/project/{}/network/private'.format(client._project))
    except APIError:
        raise
    else:
        vlans = tuple(n['vlanId'] for n in networks)

        for i in range(4001):
            if i not in vlans:
                return i

    return -1

def get_cluster_instances(client, name):
    instances = []

    try:
        all_inst = client.get('/cloud/project/{}/instance'.format(client._project))
    except APIError:
        raise
    else:
        for inst in all_inst:
            if inst['name'][:len(name)] == name:
                instances.append(inst)

    return instances

def get_cluster_networks(client, name):
    networks = []

    try:
        all_netw = client.get('/cloud/project/{}/network/private'.format(client._project))
    except APIError:
        raise
    else:
        for netw in all_netw:
            if netw['name'][:len(name)] == name:
                networks.append(netw)

    return networks
