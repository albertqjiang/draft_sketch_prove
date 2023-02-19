from setuptools import setup

with open('requirements.txt') as f:
    reqs = f.read()

setup(
    name='autoformalization',
    version='0.0.1',
    description='autoformalization',
    packages=['autoformalization'],
    install_requires=reqs.strip().split('\n'),
    include_package_data=True,
)