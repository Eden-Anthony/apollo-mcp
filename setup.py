from setuptools import setup, find_packages

setup(
    name="apollo-mcp",
    version="0.1.0",
    description="MCP server exposing Apollo.io people and organization search to AI agents",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "apollo-mcp=apollo_mcp.__main__:main",
        ],
    },
)
