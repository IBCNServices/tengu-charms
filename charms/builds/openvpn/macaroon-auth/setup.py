from setuptools import setup, find_packages

long_description = """
Python client for juju-core websocket api.
"""

setup(
    name="jujuclient",
    version="0.53.3",
    description="A juju-core/gojuju simple synchronous python api client.",
    author="Kapil Thangavelu",
    author_email="kapil.foss@gmail.com",
    url="http://juju.ubuntu.com",
    install_requires=["PyYAML", "websocket-client>=0.18.0"],
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: "
            "GNU Library or Lesser General Public License (LGPL)",
        "Intended Audience :: Developers"],
)
