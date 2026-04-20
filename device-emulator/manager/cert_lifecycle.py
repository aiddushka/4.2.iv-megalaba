import json
import signal
import subprocess
from pathlib import Path

import docker

from manager.naming import device_secret_basename, sanitize_cert_cn


class DeviceCertLifecycle:
    def __init__(
        self,
        certs_rw_dir: str,
        device_ca_cert_path: str,
        device_ca_key_path: str,
        device_certs_subdir: str = "devices",
        device_crl_path: str = "/mqtt-certs-rw/device-ca.crl",
        broker_container_name: str = "greenhouse_mqtt_broker",
    ) -> None:
        self.certs_rw_dir = certs_rw_dir
        self.device_ca_cert_path = device_ca_cert_path
        self.device_ca_key_path = device_ca_key_path
        self.device_certs_subdir = device_certs_subdir or "devices"
        self.device_crl_path = device_crl_path
        self.broker_container_name = broker_container_name

    def certs_base_dir(self) -> Path:
        return Path(self.certs_rw_dir) / self.device_certs_subdir

    def ca_db_dir(self) -> Path:
        return Path(self.certs_rw_dir) / "ca-db"

    def ca_config_path(self) -> Path:
        return self.ca_db_dir() / "openssl-ca.cnf"

    def device_paths(self, device_uid: str) -> tuple[Path, Path]:
        safe_uid = device_secret_basename(device_uid)
        base = self.certs_base_dir()
        return base / f"{safe_uid}.crt", base / f"{safe_uid}.key"

    def ensure_ca_db(self) -> Path:
        base = self.ca_db_dir()
        certs_base = self.certs_base_dir()
        base.mkdir(parents=True, exist_ok=True)
        certs_base.mkdir(parents=True, exist_ok=True)
        (base / "index.txt").touch(exist_ok=True)
        if not (base / "serial").exists():
            (base / "serial").write_text("1000\n", encoding="utf-8")
        if not (base / "crlnumber").exists():
            (base / "crlnumber").write_text("1000\n", encoding="utf-8")
        cfg = self.ca_config_path()
        cfg.write_text(
            (
                "[ ca ]\n"
                "default_ca = CA_default\n\n"
                "[ CA_default ]\n"
                f"dir = {base.as_posix()}\n"
                f"database = {(base / 'index.txt').as_posix()}\n"
                f"new_certs_dir = {certs_base.as_posix()}\n"
                f"certificate = {Path(self.device_ca_cert_path).as_posix()}\n"
                f"private_key = {Path(self.device_ca_key_path).as_posix()}\n"
                f"serial = {(base / 'serial').as_posix()}\n"
                f"crlnumber = {(base / 'crlnumber').as_posix()}\n"
                "default_md = sha256\n"
                "default_days = 365\n"
                "default_crl_days = 365\n"
                "policy = policy_any\n"
                "unique_subject = no\n"
                "x509_extensions = usr_cert\n\n"
                "[ policy_any ]\n"
                "commonName = supplied\n\n"
                "[ usr_cert ]\n"
                "basicConstraints = CA:FALSE\n"
                "keyUsage = digitalSignature,keyEncipherment\n"
                "extendedKeyUsage = clientAuth\n"
            ),
            encoding="utf-8",
        )
        return cfg

    def generate_crl(self) -> None:
        cfg = self.ensure_ca_db()
        subprocess.run(
            ["openssl", "ca", "-gencrl", "-config", str(cfg), "-out", self.device_crl_path],
            check=True,
        )

    def issue(self, device_uid: str) -> tuple[str, str]:
        cfg = self.ensure_ca_db()
        certs_base = self.certs_base_dir()
        safe_uid = device_secret_basename(device_uid)
        cert_path = certs_base / f"{safe_uid}.crt"
        key_path = certs_base / f"{safe_uid}.key"
        csr_path = certs_base / f"{safe_uid}.csr"
        subj = (
            f"/C=RU/ST=Tyumen/L=Tyumen/O=Greenhouse Dev/OU=Devices/"
            f"CN={sanitize_cert_cn(device_uid)}"
        )
        subprocess.run(["openssl", "genrsa", "-out", str(key_path), "2048"], check=True)
        subprocess.run(
            ["openssl", "req", "-new", "-key", str(key_path), "-out", str(csr_path), "-subj", subj],
            check=True,
        )
        subprocess.run(
            [
                "openssl",
                "ca",
                "-batch",
                "-config",
                str(cfg),
                "-in",
                str(csr_path),
                "-out",
                str(cert_path),
                "-notext",
            ],
            check=True,
        )
        try:
            csr_path.unlink(missing_ok=True)
        except OSError:
            pass
        self.generate_crl()
        return str(cert_path), str(key_path)

    def revoke(self, device_uid: str) -> bool:
        cfg = self.ensure_ca_db()
        cert_path, key_path = self.device_paths(device_uid)
        revoked = False
        if cert_path.is_file() and cert_path.stat().st_size > 0:
            subprocess.run(
                ["openssl", "ca", "-config", str(cfg), "-revoke", str(cert_path)],
                check=True,
            )
            revoked = True
        self.generate_crl()
        try:
            cert_path.unlink(missing_ok=True)
            key_path.unlink(missing_ok=True)
        except OSError:
            pass
        return revoked

    def rotate(self, device_uid: str) -> tuple[str, str]:
        self.revoke(device_uid)
        return self.issue(device_uid)

    def reload_mqtt_broker(self) -> None:
        try:
            docker.from_env().containers.get(self.broker_container_name).kill(signal="HUP")
            print(f"[cert] sent HUP to {self.broker_container_name} for config/CRL reload")
        except Exception as exc:
            print(f"[cert] warning: failed to reload mqtt broker ({exc})")

    def run_cli_action(self, action: str, device_uid: str) -> None:
        if action == "issue":
            cert, key = self.issue(device_uid)
            self.reload_mqtt_broker()
            print(json.dumps({"ok": True, "action": action, "device_uid": device_uid, "cert": cert, "key": key}))
            return
        if action == "rotate":
            cert, key = self.rotate(device_uid)
            self.reload_mqtt_broker()
            print(json.dumps({"ok": True, "action": action, "device_uid": device_uid, "cert": cert, "key": key}))
            return
        revoked = self.revoke(device_uid)
        self.reload_mqtt_broker()
        print(json.dumps({"ok": True, "action": action, "device_uid": device_uid, "revoked": revoked}))
