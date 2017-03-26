from setuptools import setup
import pyaimp

setup(
    name='pyaimp',
    version=pyaimp.__version__,
    description='Python AIMP remote API wrapper with some extras',
    long_description='Everything you need to know is located `here <https://epocdotfr.github.io/pyaimp/>`_.',
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
