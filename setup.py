from setuptools import setup, find_packages

setup(
    name='ppa-salvador-2018-2021',
    version='0.1',
    packages=find_packages(),
    setup_requires = [],
    install_requires=[],
    dependency_links=[],
    entry_points = {
        'console_scripts': ['ppa = ppa:main']
    }
)