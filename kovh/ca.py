from OpenSSL import crypto


class CA:
    """Generate a Certificate Authority

    Defaults based off the doc "OpenSSL Certificate Authority" by Jamie Nguyen
     - https://jamielinux.com/docs/openssl-certificate-authority/
    """

    __next_serial = 1000

    def __init__(self):
        # CA key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 4096)

        # CA cert
        cert = crypto.X509()
        cert.set_serial_number(self.__next_serial)
        cert.set_version(2)
        cert.set_pubkey(key)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)

        cacert_subject = cert.get_subject()
        cacert_subject.O = 'kOVHernetes'
        cacert_subject.OU = 'kOVHernetes Certificate Authority'
        cacert_subject.CN = 'kOVHernetes Root CA'
        cert.set_issuer(cacert_subject)

        cert.add_extensions((crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert),))
        cacert_ext = []
        cacert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', True, b'keyid:always,issuer', issuer=cert))
        cacert_ext.append(crypto.X509Extension(b'basicConstraints', True, b'CA:TRUE'))
        cacert_ext.append(crypto.X509Extension(b'keyUsage', True, b'digitalSignature, cRLSign, keyCertSign'))
        cert.add_extensions(cacert_ext)

        # sign CA cert with CA key
        cert.sign(key, 'sha256')

        type(self).__next_serial += 1

        self.cert = cert
        self.key = key

    def create_client_pair(self, ou, cn):
        """Issue a X.509 client certificate"""

        # key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # cert
        cert = crypto.X509()
        cert.set_serial_number(self.__next_serial)
        cert.set_version(2)
        cert.set_pubkey(key)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)

        cert_subject = cert.get_subject()
        cert_subject.O = 'kOVHernetes'
        cert_subject.OU = 'kOVHernetes {}'.format(ou)
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        #X509v3 extensions:
        #    X509v3 Subject Alternative Name: 
        #        DNS:host-192-168-0-1
        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'nonRepudiation, digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'clientAuth'))
        cert.add_extensions(cert_ext)

        # sign request with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return key, cert

    def create_server_pair(self, ou, cn):
        """Issue a X.509 server certificate"""

        # key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # cert
        cert = crypto.X509()
        cert.set_serial_number(self.__next_serial)
        cert.set_version(2)
        cert.set_pubkey(key)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)

        cert_subject = cert.get_subject()
        cert_subject.O = 'kOVHernetes'
        cert_subject.OU = 'kOVHernetes {}'.format(ou)
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        #X509v3 extensions:
        #    X509v3 Subject Alternative Name: 
        #        DNS:kubernetes.default.svc, DNS:kubernetes.default, DNS:kubernetes, DNS:localhost, IP Address:147.135.193.246, IP Address:10.0.0.1
        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer:always', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'serverAuth'))
        cert.add_extensions(cert_ext)

        # sign request with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return key, cert
