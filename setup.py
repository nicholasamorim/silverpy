from setuptools import setup

long_description = '''
A cross-platform python library to access Silverpop Engage and use
its interface. Library is based on Engage 8.7.
'''

setup(
    name='silverpy',
    version='0.1',
    description='An easy-to-use Silverpop Engage Library.',
    long_description=long_description,
    url='https://github.com/nicholasamorim/silverpy',
    license='GPL',
    author='Nicholas Amorim',
    author_email='nicholas@alienretro.com',
    packages=['silverpy'],
    test_suite='tests',
    install_requires=['requests', 'lxml'],
    requires=['requests', 'lxml'],
    include_package_data = True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)