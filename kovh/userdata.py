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
    'coremeta'                  : res_plain('data/systemd/coreos-metadata.service.d/10-provider.conf'),
    'coremetassh'               : res_plain('data/systemd/coreos-metadata-sshkeys@.service.d/10-provider.conf'),
    'kubelet'                   : res_plain('data/systemd/kubelet.service'),
    'etcd'                      : res_plain('data/systemd/etcd-member.service.d/10-daemon.conf'),
    'docker'                    : res_plain('data/systemd/docker.service.d/10-daemon.conf'),
    # k8s components manifests
    'apiserver'                 : res_plain('data/k8s/manifests/kube-apiserver.json'),
    'proxy'                     : res_plain('data/k8s/manifests/kube-proxy.json'),
    'controller-manager'        : res_plain('data/k8s/manifests/kube-controller-manager.json'),
    'scheduler'                 : res_plain('data/k8s/manifests/kube-scheduler.json'),
    'addon-manager'             : res_gzip('data/k8s/manifests/kube-addon-manager.yml'),
    # k8s components config
    'kubelet-config'            : res_gzip('data/k8s/kubeletconfig.json'),
    'proxy-config'              : res_gzip('data/k8s/kubeproxyconfig.json'),
    'controller-manager-config' : res_gzip('data/k8s/kubecontrollermanagerconfig.json'),
    'scheduler-config'          : res_gzip('data/k8s/kubeschedulerconfig.json'),
    # k8s addons manifests
    'kubedns'                   : res_gzip('data/k8s/addons/kubedns.yml'),
    'flannel'                   : res_gzip('data/k8s/addons/flannel.yml'),
    # k8s kubeconfig
    'kubeconfig'                : res_plain('data/k8s/kubeconfig.json')
}


class UserData:

    def __init__(self, k8s_ver='1.12.2'):
        self.k8s_ver = k8s_ver

        # boilerplate ignition config
        self.data = {
            'ignition': { 'version': '2.1.0' },
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

    def gen_kubeconfig(self, component, server='localhost'):
        """Generate kubeconfig"""

        kubeconfig = loads(files['kubeconfig'].decode(), object_pairs_hook=OrderedDict)
        kubeconfig['users'][0]['user']['client-certificate'] = 'tls/client/{}.crt'.format(component)
        kubeconfig['clusters'][0]['cluster']['server'] = 'https://' + server + ':6443'

        kubeconfig = compress((dumps(kubeconfig, indent=2) + '\n').encode())

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig-' + component + '.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(kubeconfig)
                }
            }
        ])

    def gen_kubemanifest(self, component, tag):
        """Generate Kubernetes Pod manifest"""

        manifest = loads(files[component].decode(), object_pairs_hook=OrderedDict)
        manifest['spec']['containers'][0]['image'] = 'k8s.gcr.io/hyperkube:v{}'.format(self.k8s_ver)

        manifest = compress((dumps(manifest, indent=2) + '\n').encode())

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-{}.json'.format(component) + '.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(manifest)
                }
            }
        ])

    def gen_kubelet_unit(self, roles):
        """Generate kubelet service unit"""

        labels = ("node-role.kubernetes.io/{}=''".format(r) for r in roles)

        self.add_sunits([
            {
                'name': 'kubelet.service',
                'enable': True,
                'contents': (
                    files['kubelet'].decode()
                    .replace('__IMAGE_TAG__', 'v{}'.format(self.k8s_ver))
                    .replace('__NODE_LABELS__', ','.join(labels)))
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
        hosts_content = ('127.0.0.1\tlocalhost\n' + '::1\t\tlocalhost\n' +
             '\n'.join(['{}\t{}'.format(ip, 'host-'+str(ip).replace('.', '-')) for ip in hosts]) + '\n').encode()

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/hosts',
                'mode': 420, # 0644
                'contents': {
                    'source': 'data:,' + quote(hosts_content)
                }
            }
        ])

    def gen_kube_data(self, roles):
        """Generate data deployed to all Kubernetes instances"""

        self.gen_kubelet_unit(roles)
        self.gen_kubemanifest('proxy', 'v{}'.format(self.k8s_ver))

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeletconfig.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['kubelet-config'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeproxyconfig.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['proxy-config'])
                }
            }
        ])

        # configure Docker daemon
        self.add_sunits([
            {
                'name': 'docker.service',
                'dropins': [{
                    'name': '10-daemon.conf',
                    'contents': files['docker'].decode()
                }]
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

        for component in 'apiserver', 'scheduler', 'controller-manager':
            self.gen_kubemanifest(component, 'v{}'.format(self.k8s_ver))

        self.add_files([
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubecontrollermanagerconfig.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['controller-manager-config'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeschedulerconfig.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['scheduler-config'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-addon-manager.yml' + '.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['addon-manager'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/addons/kubedns.yml' + '.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['kubedns'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/addons/flannel.yml' + '.gz',
                'mode': 416, # 0640
                'contents': {
                    'source': 'data:,' + quote(files['flannel'])
                }
            },
            {
                'filesystem': 'root',
                'path': '/opt/bin/kubectl',
                'mode': 493, # 0755
                'contents': {
                    'source': ('https://storage.googleapis.com/kubernetes-release/release/'
                               'v{}/bin/linux/amd64/kubectl').format(self.k8s_ver)
                }
            }
        ])
