from setuptools import setup, find_packages
import os
import re

# Read the version from __init__.py
with open(os.path.join('skt_dl', '__init__.py'), 'r') as f:
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]*)['\"]", f.read())
    version = version_match.group(1) if version_match else '0.0.0'

# Read README.md for the long description
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='skt-dl',
    version=version,
    description='A custom YouTube video and playlist downloader',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='skt-dl developers',
    author_email='skt-dl@example.com',
    url='https://github.com/example/skt-dl',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.0',
    ],
    entry_points={
        'console_scripts': [
            'skt-dl=skt_dl.skt_dl:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Multimedia :: Video',
        'Topic :: Internet',
    ],
    python_requires='>=3.8',
    keywords='youtube downloader video playlist',
    license='MIT',
)
