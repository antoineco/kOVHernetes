from gzip           import compress
from urllib.parse   import quote
from pkg_resources  import resource_string


def res_plain(resource):
    """Returns package data as plain bytes"""
    return resource_string(__name__, resource)

def res_gzip(resource):
    """Returns package data as gzipped bytes"""
    return compress(res_plain(resource))

# Reusable data from static files
sunits = {
    'coremeta': res_plain('data/systemd/coreos-metadata.service.d/10-provider.conf'),
    'coremetassh': res_plain('data/systemd/coreos-metadata-sshkeys@.service.d/10-provider.conf'),
    'kubelet': res_plain('data/systemd/kubelet.service'),
    'etcd': res_plain('data/systemd/etcd-member.service.d/10-cluster.conf'),
    'flanneld': res_plain('data/systemd/flanneld.service.d/10-client.conf'),
    'flanneld_netconf': res_plain('data/systemd/flanneld.service.d/10-network-config.conf')
}
k8s_manifests = {
    'apiserver': res_gzip('data/k8s/manifests/kube-apiserver.yml'),
    'proxy': res_gzip('data/k8s/manifests/kube-proxy.yml'),
    'controller_manager': res_gzip('data/k8s/manifests/kube-controller-manager.yml'),
    'scheduler': res_gzip('data/k8s/manifests/kube-scheduler.yml')
}
kubeconfig = {
    'master': res_gzip('data/k8s/kubeconfig/master.yml'),
    'node': res_gzip('data/k8s/kubeconfig/node.yml')
}


class UserData:

    def __init__(self):
        # boilerplate ignition config
        self.data = {
            'ignition': { 'version': '2.0.0' },
            'storage': {},
            'systemd': {},
            'networkd': {},
            'passwd': {}
        }

    def add_files(self, definition):
        """Add element(s) to node storage['files']"""

        if not 'files' in self.data['storage']:
            self.data['storage']['files'] = []

        if isinstance(definition, dict):
            self.data['storage']['files'].append(definition)
        elif isinstance(definition, list):
            self.data['storage']['files'].extend(definition)
        else:
            raise TypeError("'definition must be a list or a dict, not '{}'".format(type(definition)))

    def add_sunits(self, definition):
        """Add element(s) to node systemd['units']"""

        if not 'units' in self.data['systemd']:
            self.data['systemd']['units'] = []

        if isinstance(definition, dict):
            self.data['systemd']['units'].append(definition)
        elif isinstance(definition, list):
            self.data['systemd']['units'].extend(definition)
        else:
            raise TypeError("'definition must be a list or a dict, not '{}'".format(type(definition)))

    def configure_coreos_metadata(self):
        """Generate drop-ins for coreos-metadata"""
        self.add_sunits([
            {
                'name': 'coreos-metadata.service',
                'dropins': [{
                    'name': '10-provider.conf',
                    'contents': sunits['coremeta'].decode()
                }]
            },
            {
                'name': 'coreos-metadata-sshkeys@.service',
                'enable': True,
                'dropins': [{
                    'name': '10-provider.conf',
                    'contents': sunits['coremetassh'].decode()
                }]
            }
        ])

    def gen_kubemaster_data(self):
        """Generate data deployed on all Kubernetes masters"""

        self.add_sunits([
            {
                'name': 'etcd-member.service',
                'enable': True,
                'dropins': [{
                    'name': '10-cluster.conf',
                    'contents': sunits['etcd'].decode()
                }]
            },
            {
                'name': 'flanneld.service',
                'enable': True,
                'dropins': [{
                    'name': '10-network-config.conf',
                    'contents': sunits['flanneld_netconf'].decode()
                }]
            },
            {
                'name': 'kubelet.service',
                'enable': True,
                'contents': sunits['kubelet'].decode()
            }
        ])

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(kubeconfig['master'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-apiserver.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(k8s_manifests['apiserver'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-proxy.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(k8s_manifests['proxy'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-scheduler.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(k8s_manifests['scheduler'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-controller-manager.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(k8s_manifests['controller_manager'])),
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
        ])

    def gen_kubenode_data(self):
        """Generate data deployed on all Kubernetes nodes"""

        self.add_sunits([
            {
                'name': 'flanneld.service',
                'enable': True,
                'dropins': [{
                    'name': '10-client.conf',
                    'contents': sunits['flanneld'].decode()
                }]
            },
            {
                'name': 'kubelet.service',
                'enable': True,
                'contents': sunits['kubelet'].decode()
            }
        ])

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(kubeconfig['node'])),
                    'compression': 'gzip'
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-proxy.yml',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,{}'.format(quote(k8s_manifests['proxy'])),
                    'compression': 'gzip'
                }
            }
        ])

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

        self.add_files({
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 420, # 0644
            'contents': {
                'source': 'data:,{}'.format(quote(hosts_content)),
                'compression': 'gzip'
            }
        })
