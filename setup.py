from setuptools import setup, find_packages  # type: ignore

# Read the README file for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="track-cli",
    version="0.1.0",
    author="sakshamshil",
    author_email="your.email@example.com",
    description="A simple CLI tool for tracking time spent on tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sakshamshil/Timetracker",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas>=1.3.0",
        "pydantic>=1.8.0",
        "openpyxl>=3.0.0",
        "click>=8.0.0",
        "python-dateutil>=2.8.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
    ],
    keywords="time tracking, productivity, cli, timesheet",
    entry_points={
        "console_scripts": [
            "track = timetrack.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/sakshamshil/Timetracker/issues",
        "Source": "https://github.com/sakshamshil/Timetracker",
    },
)
