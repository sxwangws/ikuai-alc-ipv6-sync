# iKuai-Acl-IPv6-Sync

Automatically synchronize dynamic IPv6 addresses to iKuai ACL rules.

自动将动态 IPv6 地址同步到爱快（iKuai）ACL 规则中。

---

## ✨ Features / 功能特性

- ✅ Automatically detect current IPv6 address
- ✅ Sync to existing iKuai ACL rule (match by comment)
- ✅ Detect manual modifications
- ✅ Skip update if IP not changed
- ✅ Lightweight Docker deployment
- ✅ No SSH required
- ✅ State persistence (prevent redundant updates)

- ✅ 自动获取当前 IPv6 地址
- ✅ 通过 comment 唯一匹配爱快 ACL 规则
- ✅ 检测手动修改
- ✅ IPv6 未变化时自动跳过更新
- ✅ 轻量级 Docker 部署
- ✅ 无需 SSH 登录
- ✅ 本地状态记录避免重复更新

---

## 📦 Project Structure / 项目结构

```
ikuai-acl-ipv6-sync/
│
├── app/
│   └── main.py
├── data/
│   └── config.example.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start / 快速开始

### 1️⃣ Clone project / 克隆项目

```bash
git clone https://github.com/yourname/ikuai-acl-ipv6-sync.git
cd ikuai-acl-ipv6-sync
```

---

### 2️⃣ Prepare configuration / 准备配置文件

```bash
cp data/config.example.yml data/config.yml
```

Edit:

```
data/config.yml
```

填写你的：

- iKuai IP
- Username
- Password
- ACL rule comment

---

### 3️⃣ Run with Docker Compose / 使用 Docker Compose 运行

```bash
docker compose up -d
```

---

### 4️⃣ Check logs / 查看日志

```bash
docker logs -f ikuai-acl-ipv6-sync
```

---

## 🐳 Docker Manual Run / 手动 Docker 运行

```bash
docker run -d \
  --name ikuai-acl-ipv6-sync \
  -v $(pwd)/data:/app/data \
  yourdockerhubname/ikuai-acl-ipv6-sync:latest
```

---

## ⚙️ Configuration / 配置说明

Example config:

```yaml
ikuai:
  host: 192.168.1.1
  username: admin
  password: your_password

rule:
  comment: my-ipv6-rule
```

---

### 🔎 Rule Matching Logic / 规则匹配逻辑

- Rules are uniquely identified by `comment`
- The program reads existing rule
- Compare current IPv6 with:
  - iKuai current rule value
  - Local state.json
- Update only if changed

规则通过 comment 唯一匹配：

1. 读取爱快现有规则
2. 对比当前 IPv6
3. 若未变化 → 跳过
4. 若变化 → 更新规则
5. 更新本地 state.json

---

## 🔐 Security Notice / 安全说明

- Recommended for internal network use only
- Do NOT expose iKuai Web to public internet
- Store credentials securely
- Use firewall protection

建议：

- 仅内网使用
- 不要将爱快 Web 暴露公网
- 妥善保存密码
- 配合防火墙使用

---

## 📊 How It Works / 工作原理

1. Detect current IPv6 address
2. Login to iKuai via API
3. Find ACL rule by comment
4. Compare IPv6
5. Update if necessary
6. Save state locally

---

## 📝 Logs / 日志说明

The container outputs logs including:

- Current detected IPv6
- iKuai rule IPv6
- Update result
- Skip message

日志包含：

- 当前 IPv6
- 爱快规则 IPv6
- 更新结果
- 跳过提示

---

## 🛠 Development / 开发

Install dependencies:

```bash
pip install -r requirements.txt
```

Run manually:

```bash
python app/main.py
```

---

## 📦 Docker Image

Docker Hub:

```
https://hub.docker.com/r/yourdockerhubname/ikuai-acl-ipv6-sync
```

---

## 🗂 Versioning / 版本管理

We use semantic versioning:

- v1.0.0 – Initial stable release
- Future updates will follow semver

采用语义化版本控制。

---

## 📄 License

MIT License

See `LICENSE` file for details.

---

## 🤝 Contributing / 贡献

Pull requests are welcome.

欢迎提交 PR。

---

## ⭐ Support

If this project helps you, please give it a star ⭐
