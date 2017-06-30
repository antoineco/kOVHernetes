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
        key.generate_key(crypto.TYPE_RSA, 2048)

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

    def create_key(self):
        """Issue a X.509 key"""

        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        return key

    def create_client_cert(self, key, o, cn):
        """Issue a X.509 client certificate"""

        cert = crypto.X509()
        cert.set_serial_number(self.__next_serial)
        cert.set_version(2)
        cert.set_pubkey(key)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)

        cert_subject = cert.get_subject()
        cert_subject.O = o
        cert_subject.OU = 'kOVHernetes'
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'nonRepudiation, digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'clientAuth'))
        cert.add_extensions(cert_ext)

        # sign cert with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return cert

    def create_server_cert(self, key, o, cn, san=[]):
        """Issue a X.509 server certificate"""

        cert = crypto.X509()
        cert.set_serial_number(self.__next_serial)
        cert.set_version(2)
        cert.set_pubkey(key)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)

        cert_subject = cert.get_subject()
        cert_subject.O = o
        cert_subject.OU = 'kOVHernetes'
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer:always', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'serverAuth'))
        if san:
            cert_ext.append(crypto.X509Extension(b'subjectAltName', False, ','.join(san).encode()))
        cert.add_extensions(cert_ext)

        # sign cert with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return cert

    def create_client_pair(self, o, cn):
        """Issue a X.509 client key/certificate pair"""

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
        cert_subject.O = o
        cert_subject.OU = 'kOVHernetes'
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'nonRepudiation, digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'clientAuth'))
        cert.add_extensions(cert_ext)

        # sign cert with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return key, cert

    def create_server_pair(self, o, cn, san=[]):
        """Issue a X.509 server key/certificate pair"""

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
        cert_subject.O = o
        cert_subject.OU = 'kOVHernetes'
        cert_subject.CN = cn
        cert.set_issuer(self.cert.get_issuer())

        cert_ext = []
        cert_ext.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', cert))
        cert_ext.append(crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid,issuer:always', issuer=cert))
        cert_ext.append(crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'))
        cert_ext.append(crypto.X509Extension(b'keyUsage', True, b'digitalSignature, keyEncipherment'))
        cert_ext.append(crypto.X509Extension(b'extendedKeyUsage', True, b'serverAuth'))
        if san: cert_ext.append(crypto.X509Extension(b'subjectAltName', False, ','.join(san).encode()))
        cert.add_extensions(cert_ext)

        # sign cert with CA key
        cert.sign(self.key, 'sha256')

        type(self).__next_serial += 1

        return key, cert
