from setuptools import setup, find_packages

setup(
    name="sonic-sort",
    version="1.0.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "sonic-sort=src.cli:main",
        ],
    },
    python_requires=">=3.9",
)
