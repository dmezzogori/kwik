# Introduction

Kwik is meant to be a batteries-included web framework for building modern, RESTful backends with Python 3.10+.

As such, it handles automatically many of the tedious aspects of building a web application, such as:

 - Database connection and transaction management
 - User authentication and authorization
 - Settings management
 - Modern and consolidated best-practices, such as auditing, soft-delete, etc.

The objective of Kwik is to provide a concise API, which is easy to learn and use, and which is also easy to extend.
Kwik is operationally extensible with any existing FastAPI application.

The objective of Kwik is to uplift the developer experience, by providing a framework which is easy to use, 
and which is also easy to extend.

In the simplest of the cases, the developer just need to define the SQL models that
represent the data, and the Kwik framework will automatically provide the RESTful APIs for CRUD operations.

Kwik also aims at enabling the developer to follow efficiently the best practices of the industry,
such as Test-Driven Development. Kwik is designed to be easily testable, and it provides a set of
fixtures that can be used to test the application.

Kwik is 100% tested.