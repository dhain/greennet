from setuptools import setup, find_packages

version = '0.1.0'

setup(
    name='greennet',
    version=version,
    description=('A greenlet-based task scheduler'),
    author='David Hain',
    author_email='dhain@zognot.org',
    url='http://zognot.org/projects/greennet/',
    license='MIT',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(exclude='tests'),
    install_requires=[
        'py',
    ],
)
