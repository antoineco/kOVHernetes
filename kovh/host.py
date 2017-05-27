from json          import dumps
from gzip          import compress
from urllib.parse  import quote
from pkg_resources import resource_string

from .project import get_coreos_images

def res_raw(resource):
    return resource_string(__name__, resource)

def res_gzip(resource):
    return compress(res_raw(resource))

class Host:

    def __init__(self, name, roles, pub_net, priv_net, client):
        self.name = name
        self.roles = roles
        self.flavor = client._flavor
        self.sshkey = client._sshkey
        self.region = client._region
        self.pub_net = pub_net
        self.priv_net = priv_net

        self.image = get_coreos_images(client)[0]

        # TODO: move Ignition config management to UserData class
        self.user_data = {
            'ignition': { 'version': '2.0.0' },
            'storage': {},
            'systemd': {},
            'networkd': {},
            'passwd': {}
        }

        # --- begin /etc/hosts hack ---
        # write all subnet hosts to hosts file
        # disgusting hack to make up for OVH's terrible DNS
        # makes it possible to register k8s nodes by hostname
        from ipaddress import IPv4Network
        subnet = client.get('/cloud/project/{}/network/private/{}/subnet'.format(client._project, priv_net))[0]
        hosts = IPv4Network(subnet['cidr']).hosts()
        hosts_content = compress(
            ('127.0.0.1\tlocalhost\n' + '::1\t\tlocalhost\n' +
             '\n'.join(['{}\t{}'.format(ip, 'host-'+str(ip).replace('.', '-')) for ip in hosts]) + '\n').encode()
        )
        hosts_desc = {
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 420, # 0644
            'contents': {
                'source': 'data:,{}'.format(quote(hosts_content)),
                'compression': 'gzip'
            }
        }
        # --- end /etc/hosts hack ---

        # common units
        self.user_data['systemd']['units'] = common_units[:]

        if 'master' in self.roles:
            if not 'units' in self.user_data['systemd']:
                self.user_data['systemd']['units'] = []
            self.user_data['systemd']['units'].extend(master_sys_units)

            # Superseded by /etc/hosts hack
            #if not 'units' in self.user_data['networkd']:
            #    self.user_data['networkd']['units'] = []
            #self.user_data['networkd']['units'].extend(master_net_units)

            if not 'files' in self.user_data['storage']:
                self.user_data['storage']['files'] = []
            self.user_data['storage']['files'].extend(master_files)
            self.user_data['storage']['files'].append(hosts_desc)

        if 'node' in self.roles:
            if not 'units' in self.user_data['systemd']:
                self.user_data['systemd']['units'] = []
            self.user_data['systemd']['units'].extend(node_sys_units)

            if not 'files' in self.user_data['storage']:
                self.user_data['storage']['files'] = []
            self.user_data['storage']['files'].extend(node_files)
            self.user_data['storage']['files'].append(hosts_desc)

    def make_body(self):
        body = {
            'name': self.name,
            'flavorId': self.flavor,
            'imageId': self.image,
            'monthlyBilling': False,
            'sshKeyId': self.sshkey,
            'networks': [
                {
                    # public
                    'networkId': self.pub_net
                },
                {
                    # private
                    'networkId': self.priv_net
                }
            ],
            'region': self.region,
            'userData': dumps(self.user_data)
        }
        return body


# FILES -----------------------------------------------------------------------

kubelet = res_raw('data/systemd/kubelet.service')

kube_apiserver = res_gzip('data/k8s/manifests/kube-apiserver.yml')
kube_proxy = res_gzip('data/k8s/manifests/kube-proxy.yml')
kube_controller_manager = res_gzip('data/k8s/manifests/kube-controller-manager.yml')
kube_scheduler = res_gzip('data/k8s/manifests/kube-scheduler.yml')

kubeconfig_master = res_gzip('data/k8s/kubeconfig/kubelet-master.yml')
kubeconfig_node = res_gzip('data/k8s/kubeconfig/kubelet-node.yml')

etcd_member = res_raw('data/systemd/etcd-member.service.d/10-cluster.conf')
flanneld_net = res_raw('data/systemd/flanneld.service.d/10-network-config.conf')
flanneld_etcd = res_raw('data/systemd/flanneld.service.d/10-client.conf')

# Superseded by /etc/hosts hack
#resolved_dnsstub= res_gzip('data/systemd/resolved.conf.d/90-dns-stub.conf')
coremeta_override = res_raw('data/systemd/coreos-metadata.service.d/10-provider.conf')
coremetassh_override = res_raw('data/systemd/coreos-metadata-sshkeys@.service.d/10-provider.conf')

# IGNITION ---------------------------------------------------------------------

common_units = [
    {
        'name': 'coreos-metadata.service',
        'dropins': [{
            'name': '10-provider.conf',
            'contents': coremeta_override.decode()
        }]
    },
    {
        'name': 'coreos-metadata-sshkeys@.service',
        'enable': True,
        'dropins': [{
            'name': '10-provider.conf',
            'contents': coremetassh_override.decode()
        }]
    }
]

master_sys_units = [
    {
        'name': 'etcd-member.service',
        'enable': True,
        'dropins': [{
            'name': '10-cluster.conf',
            'contents': etcd_member.decode()
        }]
    },
    {
        'name': 'flanneld.service',
        'enable': True,
        'dropins': [{
            'name': '10-network-config.conf',
            'contents': flanneld_net.decode()
        }]
    },
    {
        'name': 'kubelet.service',
        'enable': True,
        'contents': kubelet.decode()
    }
]

node_sys_units = [
    {
        'name': 'flanneld.service',
        'enable': True,
        'dropins': [{
            'name': '10-client.conf',
            'contents': flanneld_etcd.decode()
        }]
    },
    {
        'name': 'kubelet.service',
        'enable': True,
        'contents': kubelet.decode()
    }
]

# Superseded by /etc/hosts hack
#master_net_units = [
#        {
#            'name': '10-eth0.network',
#            'contents': '[Match]\nName=eth0\n\n[Network]\nDHCP=true\n\n[DHCP]\nUseDomains=false\n'
#        },
#        {
#            'name': '10-eth1.network',
#            'contents': '[Match]\nName=eth1\n\n[Network]\nDHCP=true\nDNS=192.168.0.2\n\n[DHCP]\nUseDNS=false\nUseDomains=true\n'
#        }
#]

master_files = [
    # Superseded by /etc/hosts hack
    #{
    #    'filesystem': 'root',
    #    'path': '/etc/systemd/resolved.conf.d/90-dns-stub.conf',
    #    'mode': 420, # 0644
    #    'contents': {
    #        'source': 'data:,{}'.format(quote(resolved_dnsstub)),
    #        'compression': 'gzip'
    #    }
    #},
    {
        'filesystem': 'root',
        'path': '/var/lib/kubelet/kubeconfig',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kubeconfig_master)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/tokens.csv',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote('changeme,ovh,ovh'))
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/manifests/kube-apiserver.yml',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kube_apiserver)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/manifests/kube-proxy.yml',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kube_proxy)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/manifests/kube-scheduler.yml',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kube_scheduler)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/manifests/kube-controller-manager.yml',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kube_controller_manager)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/opt/bin/kubectl',
        'mode': 493, # 0755
        'contents': {
            'source': 'https://storage.googleapis.com/kubernetes-release/release/v1.6.4/bin/linux/amd64/kubectl'
        }
    }
]

node_files = [
    {
        'filesystem': 'root',
        'path': '/var/lib/kubelet/kubeconfig',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kubeconfig_node)),
            'compression': 'gzip'
        }
    },
    {
        'filesystem': 'root',
        'path': '/etc/kubernetes/manifests/kube-proxy.yml',
        'mode': 416, # 0640
        'contents': {
            'source': 'data:,{}'.format(quote(kube_proxy)),
            'compression': 'gzip'
        }
    }
]
