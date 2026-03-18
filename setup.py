from setuptools import setup, find_packages

setup(
    name="seanox-ai-podcast",
    version="1.0.0.0",
    packages=find_packages(),
    author="Seanox Software Solutions",
    description=(
        "Podcast generation pipeline using a YAML-defined structure and external Text-To-Speech APIs."
    ),
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/seanox/seanox-ai-podcast",
    license="Apache-2.0",
    python_requires=">=3.10",
    install_requires=[
        "PyYAML",
        "Jinja2",
        "numpy",
        "requests",
        "jmespath",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent"
    ],
    keywords=[
        "podcast", "pipeline", "text-to-speech", "yaml"
    ]
)