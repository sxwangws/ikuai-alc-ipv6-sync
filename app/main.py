# ================= main.py =================
import time
import logging
import requests
import paramiko
import hashlib
import base64
import yaml
import json
import os

CONFIG_PATH = "/app/data/config.yml"
STATE_PATH  = "/app/data/state.json"

# ================= 日志 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger()

# ================= 读取配置 =================
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

IKUAI_URL  = CONFIG["ikuai"]["url"]
IKUAI_USER = CONFIG["ikuai"]["user"]
IKUAI_PASS = CONFIG["ikuai"]["pass"]

DEFAULT_IIF = CONFIG["default_acl"]["iinterface"]
DEFAULT_OIF = CONFIG["default_acl"]["ointerface"]

SERVERS = CONFIG["servers"]
SYNC_INTERVAL = CONFIG.get("sync_interval", 300)

# ================= 状态缓存（兜底用） =================
if os.path.exists(STATE_PATH):
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            STATE = json.load(f)
    except Exception:
        STATE = {}
else:
    STATE = {}

def save_state():
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=2, ensure_ascii=False)

# ================= OpenWrt IPv6 =================
def get_ipv6_from_openwrt(ssh_cfg):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ssh_cfg["host"],
            username=ssh_cfg["user"],
            password=ssh_cfg["pass"],
            timeout=10
        )

        cmd = (
            "ubus call network.interface.lan6 status | "
            "jsonfilter -e '@[\"ipv6-address\"][*].address'"
        )
        _, stdout, _ = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        ssh.close()

        ipv6_list = [x for x in output.split() if x]
        if ipv6_list:
            logger.info(f"[OpenWrt] IPv6 = {ipv6_list}")
            return ipv6_list

        logger.warning("[OpenWrt] 未获取到 IPv6")
        return []

    except Exception as e:
        logger.error(f"[OpenWrt] 获取 IPv6 失败: {e}")
        return []

# ================= FnOS IPv6 =================
def get_ipv6_from_fnos(ssh_cfg):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ssh_cfg["host"],
            username=ssh_cfg["user"],
            password=ssh_cfg["pass"],
            timeout=10
        )

        cmd = (
            "ip -6 addr show | "
            "grep 'scope global' | grep -v temporary | "
            "awk '{print $2}' | cut -d/ -f1"
        )
        _, stdout, _ = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        ssh.close()

        ipv6_list = [x for x in output.splitlines() if x]
        if ipv6_list:
            logger.info(f"[FnOS] IPv6 = {ipv6_list}")
            return ipv6_list

        logger.warning("[FnOS] 未获取到 IPv6")
        return []

    except Exception as e:
        logger.error(f"[FnOS] 获取 IPv6 失败: {e}")
        return []

# ================= IPv6 → dst6_suffix =================
def ipv6_to_dst6_suffix(ipv6: str) -> str:
    ipv6 = ipv6.lower()

    if "::" in ipv6:
        prefix, suffix = ipv6.split("::", 1)
        parts = prefix.split(":")
        last = suffix.zfill(4)
        return (
            f"{parts[0]}:{parts[1]}:{parts[2]}:{parts[3]}"
            f":0000:0000:0000:{last}/::{last}"
        )

    parts = ipv6.split(":")
    last = parts[-1].zfill(4)
    return f"{ipv6}/::{last}"

# ================= iKuai 登录 =================
def ikuai_login(session):
    session.get(f"{IKUAI_URL}/login")

    passwd = hashlib.md5(IKUAI_PASS.encode()).hexdigest()
    salt = "salt_11" + IKUAI_PASS
    pass_b64 = base64.b64encode(salt.encode()).decode()

    payload = {
        "username": IKUAI_USER,
        "passwd": passwd,
        "pass": pass_b64,
        "remember_password": ""
    }

    session.post(
        f"{IKUAI_URL}/Action/login",
        json=payload,
        headers={"Content-Type": "application/json;charset=UTF-8"}
    )

    logger.info("[iKuai] 登录成功")

# ================= ACL 操作 =================
def get_acl_list(session):
    payload = {
        "func_name": "acl",
        "action": "show",
        "param": {
            "TYPE": "total,data",
            "limit": "0,500"
        }
    }
    r = session.post(f"{IKUAI_URL}/Action/call", json=payload)
    return r.json()["Data"]["data"]

def add_acl(session, dst6_suffix, comment, iif, oif):
    payload = {
        "func_name": "acl",
        "action": "add",
        "param": {
            "protocol": "any",
            "action": "accept",
            "dir": "forward",
            "iinterface": iif,
            "ointerface": oif,
            "dst6_mode": 1,
            "dst6_suffix": dst6_suffix,
            "ip_type": "6",
            "time": "00:00-23:59",
            "week": "1234567",
            "comment": comment,
            "enabled": "yes"
        }
    }
    session.post(f"{IKUAI_URL}/Action/call", json=payload)
    logger.info(f"[iKuai ACL] 已创建规则 {comment}")

# ⭐⭐⭐ 修复重点：完整 edit ⭐⭐⭐
def update_acl_dst6(session, rule, new_dst6):
    payload = {
        "func_name": "acl",
        "action": "edit",
        "param": {
            "id": rule["id"],
            "protocol": rule["protocol"],
            "action": rule["action"],
            "dir": rule["dir"],
            "iinterface": rule["iinterface"],
            "ointerface": rule["ointerface"],
            "dst6_mode": rule.get("dst6_mode", 1),
            "dst6_suffix": new_dst6,
            "ip_type": rule.get("ip_type", "6"),
            "time": rule.get("time", "00:00-23:59"),
            "week": rule.get("week", "1234567"),
            "comment": rule.get("comment", ""),
            "enabled": rule.get("enabled", "yes")
        }
    }

    session.post(f"{IKUAI_URL}/Action/call", json=payload)
    logger.info(f"[iKuai ACL] 已更新规则 id={rule['id']}")

# ================= 同步规则（最终稳定版） =================
def sync_rule(session, comment, dst6, iif, oif):
    rules = get_acl_list(session)
    match = [r for r in rules if r.get("comment") == comment]

    # 不存在 → 创建
    if not match:
        logger.info(f"[SYNC] {comment} 不存在，创建规则")
        add_acl(session, dst6, comment, iif, oif)
        STATE[comment] = dst6
        save_state()
        return

    rule = match[0]
    ikuai_dst6 = rule.get("dst6_suffix", "")

    # 已一致 → 跳过
    if ikuai_dst6 == dst6:
        logger.info(f"[SYNC] {comment} IPv6 未变化，跳过")
        STATE[comment] = dst6
        save_state()
        return

    # 不一致 → 强制修正
    logger.info(
        f"[SYNC] {comment} IPv6 不一致，执行修正\n"
        f"       ikuai = {ikuai_dst6}\n"
        f"       want  = {dst6}"
    )

    update_acl_dst6(session, rule, dst6)
    STATE[comment] = dst6
    save_state()

# ================= 主循环 =================
def main():
    while True:
        with requests.Session() as s:
            ikuai_login(s)

            for srv in SERVERS:
                iif = srv.get("iinterface", DEFAULT_IIF)
                oif = srv.get("ointerface", DEFAULT_OIF)

                if srv["type"] == "openwrt":
                    ipv6_list = get_ipv6_from_openwrt(srv["ssh"])
                elif srv["type"] == "fnos":
                    ipv6_list = get_ipv6_from_fnos(srv["ssh"])
                else:
                    continue

                if not ipv6_list:
                    continue

                dst6_list = sorted(
                    ipv6_to_dst6_suffix(ipv6) for ipv6 in ipv6_list
                )
                dst6 = ",".join(dst6_list)

                logger.info(
                    f"[SYNC] {srv['name']} dst6_suffix 共 {len(dst6_list)} 条"
                )

                sync_rule(s, srv["comment"], dst6, iif, oif)

        logger.info(f"[SYNC] 本轮同步完成，{SYNC_INTERVAL} 秒后再次检查")
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()