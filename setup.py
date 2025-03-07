from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="commonBird application",
    version="0.1.0",
    description="A TUI program for eBird and birdreport.cn users.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CKRainbow/commonBird",
    author="CK Rainbow",
    author_email="nanashichi@proton.me",
    license="MIT",
    keywords=["ebird", "birdreport.cn", "birder", "TUI"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    packages=find_packages(where="src"),
    package_data={},
    install_requires=["pandas", "textual", "httpx", "python-dotenv"],
    extras_require={"dev": ["textual-dev"]},
    entry_points={"console_scripts": ["run=cli:main"]},
)
