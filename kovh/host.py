from json           import dumps
from OpenSSL.crypto import dump_certificate, dump_privatekey, FILETYPE_PEM
from gzip           import compress
from urllib.parse   import quote

from .project  import get_coreos_images
from .userdata import UserData


class Host:

    def __init__(self, name, roles, pub_net, priv_net, client, ca, ip=None):
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
        self.userdata.configure_coreos_metadata()
        self.userdata.gen_etc_hosts(client, priv_net)

        if 'master' in self.roles:
            self.userdata.gen_kubemaster_data()

            # Dump X.509 CA objects
            ca_key = compress(dump_privatekey(FILETYPE_PEM, ca.key))
            ca_crt = compress(dump_certificate(FILETYPE_PEM, ca.cert))

            san = [
                'DNS:kubernetes.default.svc.cluster.local',
                'DNS:kubernetes.default.svc',
                'DNS:kubernetes.default',
                'DNS:kubernetes',
                'DNS:localhost',
                'IP:10.0.0.1'
            ]
            if ip:
                san.extend([
                    'IP:{}'.format(ip),
                    'DNS:{}'.format('host-' + ip.replace('.', '-'))
                ])

            s_key, s_crt = ca.create_server_pair(
                'k8s API server',
                'apiserver',
                san
            )
            s_key_pem = compress(dump_privatekey(FILETYPE_PEM, s_key))
            s_crt_pem = compress(dump_certificate(FILETYPE_PEM, s_crt))

            # TLS pair for kube components
            c_key, c_crt = ca.create_client_pair('k8s components', 'master')
            c_key_pem = compress(dump_privatekey(FILETYPE_PEM, c_key))
            c_crt_pem = compress(dump_certificate(FILETYPE_PEM, c_crt))

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/ca/ca.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_key)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/ca/ca.pem',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_crt)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(s_key_pem)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/apiserver.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(s_crt_pem)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_key_pem)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_crt_pem)),
                        'compression': 'gzip'
                    }
                }
            ])

        if 'node' in self.roles:
            self.userdata.gen_kubenode_data()

            # Dump X.509 CA objects
            ca_crt = compress(dump_certificate(FILETYPE_PEM, ca.cert))

            # TLS pair for kube components
            c_key, c_crt = ca.create_client_pair('k8s components', 'node')
            c_key_pem = compress(dump_privatekey(FILETYPE_PEM, c_key))
            c_crt_pem = compress(dump_certificate(FILETYPE_PEM, c_crt))

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/ca/ca.pem',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_crt)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_key_pem)),
                        'compression': 'gzip'
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(c_crt_pem)),
                        'compression': 'gzip'
                    }
                }
            ])

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
