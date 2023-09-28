"""
web_server.py

spins up a flask web server to host an api
"""


from flask import Flask


app = Flask("frankentile")


@app.route("/key-binds")
def key_binds():
    """sends back a key bindings image"""
    return "TODO!"


def init(host="127.0.0.1", port=8080):
    """starts the flask server"""
    app.run(host=host, port=port)
