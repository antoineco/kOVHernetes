from gzip          import compress
from urllib.parse  import quote
from pkg_resources import resource_string
from json          import loads, dumps
from collections   import OrderedDict


def res_plain(resource):
    """Returns package data as plain bytes"""
    return resource_string(__name__, resource)

def res_gzip(resource):
    """Returns package data as gzipped bytes"""
    return compress(res_plain(resource))

# Reusable data from static files
files = {
    # systemd units
    'coremeta'                 : res_plain('data/systemd/coreos-metadata.service.d/10-provider.conf'),
    'coremetassh'              : res_plain('data/systemd/coreos-metadata-sshkeys@.service.d/10-provider.conf'),
    'kubelet'                  : res_plain('data/systemd/kubelet.service'),
    'etcd'                     : res_plain('data/systemd/etcd-member.service.d/10-daemon.conf'),
    'flanneld'                 : res_plain('data/systemd/flanneld.service.d/10-daemon.conf'),
    'flanneld_netconf'         : res_plain('data/systemd/flanneld.service.d/10-network-config.conf'),
    # k8s components manifests
    'apiserver'                : res_gzip('data/k8s/manifests/kube-apiserver.yml'),
    'proxy'                    : res_gzip('data/k8s/manifests/kube-proxy.yml'),
    'controller_manager'       : res_gzip('data/k8s/manifests/kube-controller-manager.yml'),
    'scheduler'                : res_gzip('data/k8s/manifests/kube-scheduler.yml'),
    'addon-manager'            : res_gzip('data/k8s/manifests/kube-addon-manager.yml'),
    # k8s addons manifests
    'dashboard'                : res_gzip('data/k8s/addons/dashboard.yml'),
    'kubedns'                  : res_gzip('data/k8s/addons/kubedns.yml'),
    # k8s kubeconfig
    'kubeconfig'               : res_plain('data/k8s/kubeconfig.json')
}


class UserData:

    def __init__(self):
        # boilerplate ignition config
        self.data = {
            'ignition': { 'version': '2.0.0' },
            'storage': {},
            'systemd': {}
        }

    def add_files(self, definition):
        """Add elements to node storage['files']"""

        if not 'files' in self.data['storage']:
            self.data['storage']['files'] = []

        if isinstance(definition, list):
            self.data['storage']['files'].extend(definition)
        else:
            raise TypeError("'definition must be a list, not '{}'".format(type(definition)))

    def add_sunits(self, definition):
        """Add elements to node systemd['units']"""

        if not 'units' in self.data['systemd']:
            self.data['systemd']['units'] = []

        if isinstance(definition, list):
            self.data['systemd']['units'].extend(definition)
        else:
            raise TypeError("'definition must be a list, not '{}'".format(type(definition)))

    def configure_clinux_core(self):
        """Generate drop-ins for Container Linux core services"""

        self.add_sunits([
            {
                'name': 'coreos-metadata.service',
                'dropins': [{
                    'name': '10-provider.conf',
                    'contents': files['coremeta'].decode()
                }]
            },
            {
                'name': 'coreos-metadata-sshkeys@.service',
                'enable': True,
                'dropins': [{
                    'name': '10-provider.conf',
                    'contents': files['coremetassh'].decode()
                }]
            },
            {
                'name': 'locksmithd.service',
                'mask': True
            }
        ])

    def gen_kube_data(self):
        """Generate data deployed to all Kubernetes instances"""

        self.add_sunits([
            {
                'name': 'kubelet.service',
                'enable': True,
                'contents': files['kubelet'].decode()
            }
        ])

    def gen_kubemaster_data(self):
        """Generate data deployed to all Kubernetes masters"""

        self.add_sunits([
            {
                'name': 'etcd-member.service',
                'enable': True,
                'dropins': [{
                    'name': '10-daemon.conf',
                    'contents': files['etcd'].decode()
                }]
            }
        ])

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-apiserver.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['apiserver'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-scheduler.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['scheduler'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-controller-manager.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['controller_manager'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-addon-manager.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['addon-manager'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/addons/kubedns.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['kubedns'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/addons/dashboard.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['dashboard'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/opt/bin/kubectl',
                'mode': 493, # 0755
                'contents': {
                    'source': 'https://storage.googleapis.com/kubernetes-release/release/v1.6.6/bin/linux/amd64/kubectl'
                }
            }
        ])

    def gen_kubenode_data(self):
        """Generate data deployed to all Kubernetes nodes"""

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-proxy.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(files['proxy'])),
                    'compression': 'gzip'
                }
            }
        ])

    def gen_kubeconfig(self, component, server=None):
        """Generate kubeconfig"""

        kubeconfig = loads(files['kubeconfig'].decode(), object_pairs_hook=OrderedDict)
        kubeconfig['users'][0]['user']['client-certificate'] = 'tls/{}.crt'.format(component)

        if server:
            kubeconfig['clusters'][0]['cluster']['server'] = 'https://' + server + ':6443'

        kubeconfig = compress((dumps(kubeconfig, indent=4) + '\n').encode())

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig-{}'.format(component),
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(kubeconfig)),
                    'compression': 'gzip'
                }
            }
        ])

    def gen_flanneld_config(self, server=None, netconf=False):
        """Generate flanneld config"""

        fld_unit = {
            'name': 'flanneld.service',
            'enable': True
        }

        if server:
            fld_clconf = files['flanneld'].decode().replace('localhost', server)
        else:
            fld_clconf = files['flanneld'].decode()

        fld_unit['dropins'] = [{
            'name': '10-daemon.conf',
            'contents': fld_clconf
        }]

        if netconf:
            fld_unit['dropins'].append({
                'name': '10-network-config.conf',
                'contents': files['flanneld_netconf'].decode()
            })

        self.add_sunits([fld_unit])

    def gen_etc_hosts(self, client, net):
        """Generate /etc/hosts file containing all subnet hosts

        Makes it possible to register k8s nodes by hostname.
        Disgusting hack to make up for OVH's terrible DNS.
        """
        from ipaddress import IPv4Network

        subnet = client.get('/cloud/project/{}/network/private/{}/subnet'.format(client._project, net))[0]
        hosts = IPv4Network(subnet['cidr']).hosts()
        hosts_content = compress(
            ('127.0.0.1\tlocalhost\n' + '::1\t\tlocalhost\n' +
             '\n'.join(['{}\t{}'.format(ip, 'host-'+str(ip).replace('.', '-')) for ip in hosts]) + '\n').encode()
        )

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/hosts',
                'mode': 420, # 0644
                'contents': {
                    'source': 'data:,{}'.format(quote(hosts_content)),
                    'compression': 'gzip'
                }
            }
        ])
