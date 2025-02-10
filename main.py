from flask import Flask, render_template
import requests
import socket
import yaml
import os

app = Flask(__name__)
app.config["BASE_PATH"] = os.getenv("BASE_PATH", "/")


def load_services_config(config_path="config.yaml"):
    """
    Load service definitions from a YAML config file.
    """
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("services", [])


def check_openvpn(url):
    """
    Check if an OpenVPN server is reachable (without configs).
    """
    host, port = url.split("://")[-1].split(":")
    try:
        with socket.create_connection((host, port), timeout=3) as sock:
            sock.settimeout(3)
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
        resp = requests.get(url, proxies={surl[0]: surl[1]}, timeout=3)
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
        resp = requests.get(url, timeout=3)
        return resp.ok or resp.status_code in [401, 403]
    except Exception as e:
        e_m = str(e)
        if "Failed to resolve" in e_m:
            return False, "Failed to resolve host, check https://dnschecker.org/#A to see DNS propagation."
        return False, e_m


@app.route(app.config["BASE_PATH"], methods=["GET"])
def index():
    services = load_services_config(os.getenv("CONFIG_PATH", "config.yaml"))
    service_statuses = []

    for service in services:
        service_type = service.get("type")
        service_url = service.get("url")
        service_name = service.get("name", "Unknown Service")

        if service_type == "openvpn":
            status = check_openvpn(service_url)
        elif service_type == "proxy":
            status = check_proxy(service_url)
        else:
            status = check_generic(service_url)

        service_statuses.append({
            "name": service_name,
            "type": service_type,
            "reason": "" if isinstance(status, bool) else status[1],
            "url": service_url,
            "is_up": status if isinstance(status, bool) else status[0]
        })

    return render_template("index.html", services=service_statuses)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)