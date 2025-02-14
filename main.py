from flask import Flask, render_template, request
from functools import wraps
import concurrent.futures
import datetime
import requests
import socket
import yaml
import time
import os

app = Flask(__name__)
app.config["BASE_PATH"] = os.getenv("BASE_PATH", "/")
app.config["ADMIN_MESSAGE"] = ""
app.config["ADMIN_MESSAGE_TIME"] = time.time()
app.config["ADMIN_MESSAGE_EXPIRATION_TIME"] = 86400


def login_required(f):
    @wraps(f)
    def wrapped_view(**kwargs):
        auth = request.authorization
        if not (auth and check_auth(auth.username, auth.password)):
            return ('Unauthorized', 401, {
                'WWW-Authenticate': 'Basic realm="Login Required"'
            })

        return f(**kwargs)

    return wrapped_view


def check_auth(username, password):
    admin_user = os.getenv("ADMIN_USER")
    admin_password = os.getenv("ADMIN_PASSWORD")
    return username == admin_user and password == admin_password


def load_services_config(config_path="config.yaml", config_name="services"):
    """
    Load service definitions from a YAML config file.
    """
    if app.config["ADMIN_MESSAGE_TIME"] != "" and abs(time.time() - app.config["ADMIN_MESSAGE_TIME"]) > app.config["ADMIN_MESSAGE_EXPIRATION_TIME"]:
        app.config["ADMIN_MESSAGE"] = ""
        app.config["ADMIN_MESSAGE_TIME"] = time.time()
        app.config["ADMIN_MESSAGE_EXPIRATION_TIME"] = 86400

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get(config_name, [])


def check_openvpn(url):
    """
    Check if an OpenVPN server is reachable (without configs).
    """
    host, port = url.split("://")[-1].split(":")
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.settimeout(5)
            try:
                response = sock.recv(1024)
                if response:
                    return True
                else:
                    return True
            except socket.timeout:
                return True
            except Exception as e:
                return False, str(e)

    except ConnectionRefusedError:
        return False
    except socket.timeout:
        return False
    except socket.gaierror:
        return False
    except Exception as e:
        e_m = str(e)
        if "Failed to resolve" in e_m:
            return False, "Failed to resolve host, check https://dnschecker.org/#A to see DNS propagation."
        return False, e_m


def check_proxy(url):
    """
    Check if a proxy server is reachable (without proxy credentials).
    """
    try:
        surl = url.split("://")
        resp = requests.get(url, proxies={surl[0]: surl[1]}, timeout=10)
        return resp.ok or resp.status_code in [407]
    except Exception as e:
        e_m = str(e)
        if "Failed to resolve" in e_m:
            return False, "Failed to resolve host, check https://dnschecker.org/#A to see DNS propagation."
        return False, e_m


def check_generic(url):
    """
    Generic check for any HTTP endpoint.
    """
    try:
        resp = requests.get(url, timeout=10)
        return resp.ok or resp.status_code in [401, 403]
    except Exception as e:
        e_m = str(e)
        if "Failed to resolve" in e_m:
            return False, "Failed to resolve host, check https://dnschecker.org/#A to see DNS propagation."
        return False, e_m


def get_services(config_name="services"):
    services = load_services_config(os.getenv("CONFIG_PATH", "config.yaml"), config_name)
    service_statuses = []
    tasks = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:

        for service in services:
            service_type = service.get("type")
            service_url = service.get("url")
            service_name = service.get("name", "Unknown Service")

            if service_type == "openvpn":
                tasks[service_name] = executor.submit(check_openvpn, service_url)
            elif service_type == "proxy":
                tasks[service_name] = executor.submit(check_proxy, service_url)
            else:
                tasks[service_name] = executor.submit(check_generic, service_url)

        for service in services:
            service_type = service.get("type")
            service_url = service.get("url")
            service_name = service.get("name", "Unknown Service")
            status = tasks[service_name].result()

            service_statuses.append({
                "name": service_name,
                "type": service_type,
                "reason": "" if isinstance(status, bool) else status[1],
                "url": service_url,
                "is_up": status if isinstance(status, bool) else status[0]
            })

    print(f'[{datetime.datetime.now()}] {" ".join(["%s %r;" % (ss["name"], ss["is_up"]) for ss in service_statuses])}')
    return service_statuses


@app.route(app.config["BASE_PATH"], methods=["GET"])
def index():
    service_statuses = get_services()
    return render_template("index.html", services=service_statuses, admin_message=app.config["ADMIN_MESSAGE"])


@app.route(f'{app.config["BASE_PATH"].removesuffix("/")}/admin', methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        message = request.form.get("admin_message", "")
        et = float(request.form.get("expiration_time", app.config["ADMIN_MESSAGE_EXPIRATION_TIME"]/3600))
        app.config["ADMIN_MESSAGE"] = message
        app.config["ADMIN_MESSAGE_TIME"] = time.time()
        app.config["ADMIN_MESSAGE_EXPIRATION_TIME"] = int(et*3600) if et > 0 else app.config["ADMIN_MESSAGE_EXPIRATION_TIME"]

    service_statuses = get_services("admin-services")
    return render_template("admin.html", services=service_statuses)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)