from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="easyqiwi",
    version="1.0.1",
    author="Maehdakvan",
    author_email="visitanimation@google.com",
    description="Асинхронный Python модуль для работы с QIWI API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DedInc/easyqiwi",
    project_urls={
        "Bug Tracker": "https://github.com/DedInc/easyqiwi/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    install_requires=['asyncio', 'httpx', 'httpx-socks', 'httpx-socks[asyncio]', 'httpx-socks[trio]'],
    python_requires='>=3.6'
)
