from setuptools import setup, find_packages
from kovh       import __version__

setup(
    # Package info
    name='kOVHernetes',
    version=__version__,
    description='Manage Kubernetes clusters on the OVH Cloud platform',
    packages=find_packages(),

    # Data
    package_data={
        'kovh': [
            'data/k8s/*/*.yml',
            'data/k8s/manifests/*.json',
            'data/k8s/kubeconfig.json',
            'data/systemd/*.service',
            'data/systemd/*/*.conf'
        ]
    },

    # Dependencies
    install_requires=[
        'docopt>=0.6.2',
        'ovh>=0.4.7',
        'pyOpenSSL>=17.0.0'
    ],

    # Script info
    entry_points={
        'console_scripts': [
            'kovh = kovh.main:main'
        ]
    },

    # Author
    author='Antoine Cotten',
    author_email='tonio.cotten@gmail.com',

    # Metadata
    license='Apache 2.0',
    keywords='kubernetes ovh coreos',
    url='https://github.com/antoineco/kOVHernetes'
)
