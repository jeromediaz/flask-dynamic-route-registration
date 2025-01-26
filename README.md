# Flask dynamic route registration

A library to help dynamically register routes in Flask applications.

```bash
pip install flask-dynamic-route-registration
```

## How to Use
### Basic Setup

You start by creating a Flask application as you usually do.

```python
from flask import Flask
from flask_dynamic_route_registration import register_blueprint

app = Flask(__name__)

register_blueprint(app, "healthcheck", '')

app.run()
```

Inside the healthcheck.__init__.py file


```python
from flask import make_response
from typing import TYPE_CHECKING

from flask_dynamic_route_registration import register_route

if TYPE_CHECKING:
    from flask import Response

@register_route("/health")
def health() -> "Response":
    response = make_response("OK", 200)
    response.mimetype = "text/plain"
    return response
    
```


### More advanced usage
In this usage, we will cover both:
- how to reuse the same file multiple times but with different parameters,
- how to register a route based on a condition

```python


api_versions = [
    {
        "blueprint_name": "api_v1",
        "blueprint_kwargs": {"url_prefix": "/api/1"},
        "params": {"version": 1},
    },
    {
        "blueprint_name": "api_v2",
        "blueprint_kwargs": {"url_prefix": "/api/2"},
        "params": {"version": 2},
    }
]

register_blueprint(app, 'api', api_versions)

```



Inside the api.__init__.py file


```python
from flask import jsonify
from typing import TYPE_CHECKING

from flask_dynamic_route_registration import register_route

if TYPE_CHECKING:
    from flask import Response

@register_route("/status")
def status(*, version: int = 1) -> "Response":
    return jsonify({"status": "OK", "version": version})
    

@register_route("/foo", enabled=lambda **params: params.get("version", 1) >= 2)
def new_endpoint(*, version: int = 1) -> Response:

    return jsonify({"hello": "world"})

```

By doing so we have registered three routes:

| URL           | Return value                   |
|---------------|--------------------------------|
| /api/1/status | {"status": "OK", "version": 1} |
| /api/2/status | {"status": "OK", "version": 2} |
| /api/2/foo    | {"hello": "world"}             |


## License

This project is licensed under the MIT License - see the LICENSE file for details.