from setuptools import setup
from os import path
import pyaimp

setup(
    name='pyaimp',
    version=pyaimp.__version__,
    description='AIMP remote API wrapper for Python',
    long_description='You can find the documentation `here <https://github.com/EpocDotFr/pyaimp#readme>`_.',
    url='https://github.com/EpocDotFr/pyaimp',
    author='Maxime "Epoc" G.',
    author_email='contact.nospam@epoc.nospam.fr',
    license='DBAD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3.5',
        'Operating System :: Microsoft :: Windows'
    ],
    keywords='aimp remote api wrapper client',
    py_modules=['pyaimp'],
    download_url='https://github.com/EpocDotFr/pyaimp/archive/pyaimp-{version}.tar.gz'.format(version=pyaimp.__version__)
)