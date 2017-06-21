from json           import dumps
from OpenSSL.crypto import dump_certificate, dump_privatekey, FILETYPE_PEM
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

        if any([r in self.roles for r in ['master', 'node']]):
            self.userdata.gen_kube_data()

            # Dump X.509 CA cert
            ca_crt = dump_certificate(FILETYPE_PEM, ca.cert)

            # TLS client pair for kube components
            kc_key, kc_crt = ca.create_client_pair('system:nodes', 'k8s-client')
            kc_key_pem = dump_privatekey(FILETYPE_PEM, kc_key)
            kc_crt_pem = dump_certificate(FILETYPE_PEM, kc_crt)

            # TLS client pair for etcd
            ec_key, ec_crt = ca.create_client_pair('etcd', 'etcd-client')
            ec_key_pem = dump_privatekey(FILETYPE_PEM, ec_key)
            ec_crt_pem = dump_certificate(FILETYPE_PEM, ec_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.pem',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_crt))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/k8s_c.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(kc_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/k8s_c.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(kc_crt_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd_c.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(ec_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd_c.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ec_crt_pem))
                    }
                }
            ])

        if 'master' in self.roles:
            self.userdata.gen_kubemaster_data()

            # Dump X.509 CA key
            ca_key = dump_privatekey(FILETYPE_PEM, ca.key)

            # TLS server pair for kube API server
            ks_san = [
                'DNS:kubernetes.default.svc.cluster.local',
                'DNS:kubernetes.default.svc',
                'DNS:kubernetes.default',
                'DNS:kubernetes',
                'DNS:localhost',
                'IP:10.0.0.1'
            ]
            if ip:
                ks_san.extend([
                    'IP:{}'.format(ip),
                    'DNS:{}'.format('host-' + ip.replace('.', '-'))
                ])

            ks_key, ks_crt = ca.create_server_pair('Kubernetes', 'apiserver', ks_san)
            ks_key_pem = dump_privatekey(FILETYPE_PEM, ks_key)
            ks_crt_pem = dump_certificate(FILETYPE_PEM, ks_crt)

            # TLS server pair for etcd
            es_san = ['DNS:localhost']
            if ip:
                es_san.append('IP:{}'.format(ip))

            es_key, es_crt = ca.create_server_pair('etcd', 'master', es_san)
            es_key_pem = dump_privatekey(FILETYPE_PEM, es_key)
            es_crt_pem = dump_certificate(FILETYPE_PEM, es_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(ca_key))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/k8s_s.key',
                    'mode': 384, # 0600
                    'contents': {
                        'source': 'data:,{}'.format(quote(ks_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/k8s_s.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(ks_crt_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd_s.key',
                    'mode': 384, # 0600
                    'user': {
                        'id': 232 # etcd user id
                    },
                    'contents': {
                        'source': 'data:,{}'.format(quote(es_key_pem))
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/etcd_s.crt',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,{}'.format(quote(es_crt_pem))
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
