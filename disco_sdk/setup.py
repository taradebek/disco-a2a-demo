"""
Disco SDK Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="disco-sdk",
    version="1.0.0",
    author="Disco Team",
    author_email="developers@disco.ai",
    description="Multi-Agent Payment Infrastructure - Enable your AI agents to pay each other seamlessly",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/disco-ai/disco-sdk-python",
    project_urls={
        "Documentation": "https://docs.disco.ai",
        "Homepage": "https://disco.ai",
        "Repository": "https://github.com/disco-ai/disco-sdk-python",
        "Bug Reports": "https://github.com/disco-ai/disco-sdk-python/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business :: Financial :: Payment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "asyncio",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "myst-parser>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "disco=disco_sdk.cli:main",
        ],
    },
    keywords=[
        "ai", "agents", "payments", "multi-agent", "fintech", 
        "automation", "api", "sdk", "disco"
    ],
    include_package_data=True,
    zip_safe=False,
) 