# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['kwik',
 'kwik.api',
 'kwik.api.endpoints',
 'kwik.core',
 'kwik.crud',
 'kwik.database',
 'kwik.exceptions',
 'kwik.exporters',
 'kwik.logger',
 'kwik.middlewares',
 'kwik.models',
 'kwik.routers',
 'kwik.schemas',
 'kwik.schemas.mixins',
 'kwik.tests',
 'kwik.tests.utils',
 'kwik.typings',
 'kwik.utils',
 'kwik.websocket']

package_data = \
{'': ['*']}

install_requires = \
['aiofiles>=22.1.0,<23.0.0',
 'alembic>=1.8.1,<2.0.0',
 'asyncpg>=0.27.0,<0.28.0',
 'broadcaster>=0.2.0,<0.3.0',
 'fastapi>=0.87.0,<0.88.0',
 'httptools>=0.5.0,<0.6.0',
 'passlib>=1.7.4,<2.0.0',
 'psycopg2-binary>=2.9.5,<3.0.0',
 'pydantic[email]>=1.10.2,<2.0.0',
 'python-jose>=3.3.0,<4.0.0',
 'python-multipart>=0.0.5,<0.0.6',
 'sqlalchemy>=1.4.44,<2.0.0',
 'uvicorn>=0.20.0,<0.21.0',
 'websockets>=10.4,<11.0']

setup_kwargs = {
    'name': 'kwik',
    'version': '0.1.0',
    'description': '',
    'long_description': '# Kwik\n\n![Logo](docs/handbook/docs/img/logo.png)\n\n---\n\n**Documentation**: https://kwik.rocks\n\n**Repository**: https://github.com/dmezzogori/kwik\n\n---\n\nKwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.10+.\n  Kwik is based on FastAPI, builds upon it and delivers an opinionated concise, business-oriented API.\n\nThe key features are:\n\n\n* **Conciseness**: Kwik is quick (pun-intended :smile:)\n* **Battle-tested**: developed internally at [Kheperer](https://kheperer.it), we use it every day to build robust and modern solutions for our customers.\n* **Standards-based**\n\n> :warning:\n> While Kwik is in active development, and already used for production, it is still in a **pre-release state**.\n> **The API is subject to change**, and the documentation is not complete yet.\n\n\n## Acknowledgments\n\nPython 3.10+\n\nKwik stands on the shoulder of a couple of giants:\n\n* [FastAPI](https://fastapi.tiangolo.com/): for the web parts.\n* [SQLAlchemy](https://www.sqlalchemy.org/): for the ORM part.\n\n## Installation\n\n```console\n$ pip install kwik\n```\n\nIt will install kwik and all its dependencies.\n\n## Example\n\n### Run it\n\n```console\n$ python -m kwik\n```\n\n\nIf kwik is started in this way, it automatically creates a development server on port `8080`, with hot-reloading enabled\n\n\n### Check it\n\nOpen your browser at http://localhost:8080/docs.\n\nYou will see the automatic interactive API documentation, showing the built-in endpoints and schemas.\n\n![OpenAPI](docs/handbook/docs/img/openapi.jpeg)\n\n\n## License\n\nThis project is licensed under the terms of the MIT license.\n',
    'author': 'Davide Mezzogori',
    'author_email': 'dmezzogori@users.noreply.github.com',
    'maintainer': 'None',
    'maintainer_email': 'None',
    'url': 'None',
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.10,<4.0',
}


setup(**setup_kwargs)
