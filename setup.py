import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="chronobiology",
    version="0.0.4",
    author="Ruslan Konovalov",
    author_email="konovalov.rus@sjtu.edu.cn",
    description="Package for chronobiology analysis",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/ruslands/Chronobiology",
    download_url="https://github.com/ruslands/Chronobiology/archive/v0.0.3.tar.gz",
    keywords=['chronobiology','actogram','periodogram','sleep','analysis'],
    install_requires=['influxdb', 'pandas', 'numpy', 'matplotlib', 'scipy'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
