import os

from setuptools import find_packages, setup

_HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(_HERE, 'README.md'), 'r') as f:
    long_desc = f.read()

setup(
    name='hyp3_sdk',
    use_scm_version=True,
    description='A python wrapper around the HyP3 API',
    long_description=long_desc,
    long_description_content_type='text/markdown',

    url='https://github.com/ASFHyP3/hyp3-sdk',

    author='ASF APD/Tools Team',
    author_email='uaf-asf-apd@alaska.edu',

    license='BSD',
    include_package_data=True,

    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    python_requires='~=3.8',

    install_requires=[
        'python-dateutil',
        'requests',
        'urllib3',
        'tqdm',
    ],

    extras_require={
        'develop': [
            'pytest',
            'pytest-cov',
            'responses',
        ]
    },

    packages=find_packages(),

    zip_safe=False,
)
