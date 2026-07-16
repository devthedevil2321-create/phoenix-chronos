from setuptools import setup, find_packages

setup(
    name="phoenix-chronos",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "chronos=chronos.cli:main",
        ],
    },
)
