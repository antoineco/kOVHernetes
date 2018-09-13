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
            self.userdata.gen_kube_data(self.roles)

            # Dump X.509 CA cert
            ca_crt_pem = dump_certificate(FILETYPE_PEM, ca.cert)

            # we generate a single RSA key per host due to User Data size limit of 65535 bytes (base64-encoded)
            key = ca.create_key()
            key_pem = dump_privatekey(FILETYPE_PEM, key)

            # TLS client certificates
            kubelet_client_crt = ca.create_client_cert(key, 'system:nodes', 'system:node:host-' + ip.replace('.', '-'))
            kubelet_client_crt_pem = dump_certificate(FILETYPE_PEM, kubelet_client_crt)
            proxy_client_crt = ca.create_client_cert(key, 'Kubernetes', 'system:kube-proxy')
            proxy_client_crt_pem = dump_certificate(FILETYPE_PEM, proxy_client_crt)

            # TLS server certificates
            kubelet_server_crt = ca.create_server_cert(key, 'Kubernetes', 'host-' + ip.replace('.', '-'))
            kubelet_server_crt_pem = dump_certificate(FILETYPE_PEM, kubelet_server_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/host.key',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.pem',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(ca_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/kubelet.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(kubelet_client_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/server/kubelet.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(kubelet_server_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/proxy.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(proxy_client_crt_pem)
                    }
                }
            ])

        if 'master' in self.roles:
            self.userdata.gen_kubemaster_data()

            # Dump X.509 CA key
            ca_key_pem = dump_privatekey(FILETYPE_PEM, ca.key)

            # TLS server pair for kube API server
            apiserver_san = [
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
            apiserver_crt = ca.create_server_cert(key, 'Kubernetes', 'apiserver', apiserver_san)
            apiserver_crt_pem = dump_certificate(FILETYPE_PEM, apiserver_crt)

            # TLS server pair for etcd member
            etcd_san = [
                'DNS:localhost',
                'IP:127.0.0.1',
                'DNS:' + 'host-' + ip.replace('.', '-'),
                'IP:' + ip
            ]
            etcd_member_crt = ca.create_server_cert(key, 'etcd', 'member', etcd_san)
            etcd_member_crt_pem = dump_certificate(FILETYPE_PEM, etcd_member_crt)

            # TLS client certificates
            cm_crt = ca.create_client_cert(key, 'Kubernetes', 'system:kube-controller-manager')
            cm_crt_pem = dump_certificate(FILETYPE_PEM, cm_crt)
            scheduler_crt = ca.create_client_cert(key, 'Kubernetes', 'system:kube-scheduler')
            scheduler_crt_pem = dump_certificate(FILETYPE_PEM, scheduler_crt)
            apiserver_client_crt = ca.create_client_cert(key, 'system:masters', 'apiserver:host-' + ip.replace('.', '-'))
            apiserver_client_crt_pem = dump_certificate(FILETYPE_PEM, apiserver_client_crt)
            etcd_client_crt = ca.create_client_cert(key, 'etcd', 'root')
            etcd_client_crt_pem = dump_certificate(FILETYPE_PEM, etcd_client_crt)

            self.userdata.add_files ([
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/ca.key',
                    'mode': 416, # 0640
                    'contents': {
                        'source': 'data:,' + quote(ca_key_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/server/apiserver.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(apiserver_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/server/etcd.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(etcd_member_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/controller-manager.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(cm_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/scheduler.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(scheduler_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/apiserver.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(apiserver_client_crt_pem)
                    }
                },
                {
                    'filesystem': 'root',
                    'path': '/etc/kubernetes/tls/client/etcd.crt',
                    'mode': 420, # 0644
                    'contents': {
                        'source': 'data:,' + quote(etcd_client_crt_pem)
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
            'userData': dumps(self.userdata.data, separators=(',', ':'))
        }
        return body
