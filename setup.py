from setuptools import setup, find_packages  # type: ignore

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
        "python-dateutil",
    ],
    entry_points={
        "console_scripts": [
            "track = timetrack.cli:main",
        ],
    },
)
