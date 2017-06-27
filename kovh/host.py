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

            # TLS client pair
            c_key, c_crt = ca.create_client_pair('system:nodes', 'system:node:host-' + ip.replace('.', '-'))
            c_key_pem = dump_privatekey(FILETYPE_PEM, c_key)
            c_crt_pem = dump_certificate(FILETYPE_PEM, c_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.pem',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_crt_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_crt_pem))
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
                'DNS:{}'.format('host-' + ip.replace('.', '-')),
                'IP:{}'.format(ip)
            ]
            api_key, api_crt = ca.create_server_pair('Kubernetes', 'apiserver', api_san)
            api_key_pem = dump_privatekey(FILETYPE_PEM, api_key)
            api_crt_pem = dump_certificate(FILETYPE_PEM, api_crt)

            # TLS server pair for etcd member
            etcd_san = [
                'DNS:localhost',
                'IP:127.0.0.1',
                'DNS:{}'.format('host-' + ip.replace('.', '-')),
                'IP:{}'.format(ip)
            ]
            etcd_key, etcd_crt = ca.create_server_pair('etcd', 'master', etcd_san)
            etcd_key_pem = dump_privatekey(FILETYPE_PEM, etcd_key)
            etcd_crt_pem = dump_certificate(FILETYPE_PEM, etcd_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(api_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(api_crt_pem))
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
                        'source': 'data:,{}'.format(quote(etcd_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(etcd_crt_pem))
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
            'userData': dumps(self.userdata.data)
        }
        return body
