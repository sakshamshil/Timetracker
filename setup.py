from setuptools import setup, find_packages

setup(
    name="track",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas",
        "pydantic",
        "openpyxl",
        "click",
    ],
    entry_points={
        "console_scripts": [
            "track = timetrack.cli:main",
        ],
    },
)
