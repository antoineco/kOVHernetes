from json           import dumps
from OpenSSL.crypto import dump_certificate, dump_privatekey, FILETYPE_PEM
from urllib.parse   import quote

from .project  import get_coreos_images
from .userdata import UserData


class Host:

    def __init__(self, name, roles, pub_net, priv_net, client, ca, ip):
        self.name = name
        self.roles = roles
        self.flavor = client._flavor
        self.sshkey = client._sshkey
        self.region = client._region
        self.pub_net = pub_net
        self.priv_net = priv_net
        self.ip = ip

        self.image = get_coreos_images(client)[0]

        self.userdata = UserData()
        self.userdata.configure_clinux_core()
        self.userdata.gen_etc_hosts(client, priv_net)

        if any([r in self.roles for r in ['master', 'node']]):
            self.userdata.gen_kube_data()

            # Dump X.509 CA cert
            ca_crt_pem = dump_certificate(FILETYPE_PEM, ca.cert)

            # TLS client certificates
            # we use a single client key per host due to User Data size limit of 65535 bytes (base64-encoded)
            client_key = ca.create_key()
            client_key_pem = dump_privatekey(FILETYPE_PEM, client_key)
            kubelet_crt = ca.create_client_cert(client_key, 'system:nodes', 'system:node:host-' + ip.replace('.', '-'))
            kubelet_crt_pem = dump_certificate(FILETYPE_PEM, kubelet_crt)
            proxy_crt = ca.create_client_cert(client_key, 'Kubernetes', 'system:kube-proxy')
            proxy_crt_pem = dump_certificate(FILETYPE_PEM, proxy_crt)
            etcd_client_crt = ca.create_client_cert(client_key, 'etcd', 'root')
            etcd_client_crt_pem = dump_certificate(FILETYPE_PEM, etcd_client_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.pem',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(ca_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,' + quote(client_key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/kubelet.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(kubelet_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/proxy.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(proxy_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcdclient.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(etcd_client_crt_pem)
                    }
                }

            ])

        if 'master' in self.roles:
            self.userdata.gen_kubemaster_data()

            # Dump X.509 CA key
            ca_key_pem = dump_privatekey(FILETYPE_PEM, ca.key)

            # TLS server pair for kube API server
            api_san = [
                'DNS:kubernetes.default.svc.cluster.local',
                'DNS:kubernetes.default.svc',
                'DNS:kubernetes.default',
                'DNS:kubernetes',
                'IP:10.0.0.1',
                'DNS:localhost',
                'IP:127.0.0.1',
                'DNS:' + 'host-' + ip.replace('.', '-'),
                'IP:' + ip
            ]
            api_key, api_crt = ca.create_server_pair('Kubernetes', 'apiserver', api_san)
            api_key_pem = dump_privatekey(FILETYPE_PEM, api_key)
            api_crt_pem = dump_certificate(FILETYPE_PEM, api_crt)

            # TLS server pair for etcd member
            etcd_san = [
                'DNS:localhost',
                'IP:127.0.0.1',
                'DNS:' + 'host-' + ip.replace('.', '-'),
                'IP:' + ip
            ]
            etcd_member_key, etcd_member_crt = ca.create_server_pair('etcd', 'member', etcd_san)
            etcd_member_key_pem = dump_privatekey(FILETYPE_PEM, etcd_member_key)
            etcd_member_crt_pem = dump_certificate(FILETYPE_PEM, etcd_member_crt)

            # TLS client certificates
            cm_crt = ca.create_client_cert(client_key, 'Kubernetes', 'system:kube-controller-manager')
            cm_crt_pem = dump_certificate(FILETYPE_PEM, cm_crt)
            scheduler_crt = ca.create_client_cert(client_key, 'Kubernetes', 'system:kube-scheduler')
            scheduler_crt_pem = dump_certificate(FILETYPE_PEM, scheduler_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,' + quote(ca_key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,' + quote(api_key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(api_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd.key',
                    'mode': 384, # 0600
                    'user': {
                        'id': 232 # etcd user id
                    },
                    'contents': {
                        'source': 'data:,' + quote(etcd_member_key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(etcd_member_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/controller-manager.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(cm_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/scheduler.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(scheduler_crt_pem)
                    }
                }
            ])

        if 'node' in self.roles:
            self.userdata.gen_kubenode_data()

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
                    'networkId': self.priv_net,
                    'ip': self.ip
                }
            ],
            'region': self.region,
            'userData': dumps(self.userdata.data, separators=(',', ':'))
        }
        return body
