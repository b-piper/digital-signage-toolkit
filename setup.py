#!/usr/bin/env python3
"""Setup script for Digital Signage Toolkit."""
from pathlib import Path

from setuptools import find_packages, setup

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="digital-signage-toolkit",
    version="2.4.4",
    description="Professional GUI application for provisioning and maintaining Ubuntu Digital Signage Kiosks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Southwestern CC IT",
    author_email="it@southwesterncc.edu",
    url="https://github.com/southwesterncc/digital-signage-toolkit",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PyQt6>=6.6.0",
        "psutil>=5.9.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "digital-signage-toolkit=digital_signage_toolkit.main:main",
        ],
        "gui_scripts": [
            "digital-signage-toolkit=digital_signage_toolkit.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
    ],
    package_data={
        "digital_signage_toolkit": [],
    },
)

