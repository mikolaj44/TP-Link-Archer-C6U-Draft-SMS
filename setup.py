import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tplinkrouterc6udraftsms",
    version="1.0",
    author="mikolaj44",
    description="TP-Link Router API (supports also Mercusys Router)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mikolaj44/TP-Link-Archer-C6U-Draft-SMS",
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    install_requires=['requests', 'pycryptodome', 'macaddress', 'tqdm'],
    python_requires='>=3.10',
)
