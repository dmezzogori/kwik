---
title: Kwik
---


---

**Documentation**: https://kwik.rocks

**Repository**: https://github.com/dmezzogori/kwik

---

Kwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.9+.
  Kwik is based on FastAPI, builds upon it and delivers an opinionated concise API.

The key features are:


* **Conciseness**: Kwik is quick (pun-intended :smile:)
* **Battle-tested**: developed internally at Kheperer, we use it everyday to build robust and modern solutions for our customers.
* **Standards-based**

## Acknowledgments

Python 3.10+

Kwik stands on the shoulder of a couple of giants:

* [FastAPI](https://fastapi.tiangolo.com/): for the web parts.
* [SQLAlchemy](https://www.sqlalchemy.org/): for the ORM part.

## Installation

<div class="termy">

```console
$ pip install kwik
---> 100%
Installed
```

</div>

It will install kwik and all its dependencies.

## Example

### Run it

<div class="termy">

```console
$ python -m kwik
Uvicorn running on http://localhost:8080 (Press CTRL+C to quit)
```

</div>

If kwik is started in this way, it automatically create a development server on port `8080`, with hot-reloading enabled


### Check it

Open your browser at http://127.0.0.1/docs.

You will see the automatic interactive API documentation, showing the built-in endpoints and schemas.

![OpenAPI](img/openapi.jpeg)



## License

This project is licensed under the terms of the MIT license.
