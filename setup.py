import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bdict",
    version="0.1.0b3",
    author="Bar Harel",
    python_requires='>=3.6',
    author_email="bzvi7919@gmail.com",
    description="Python auto-binding dict",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bharel/bdict",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    )
)
