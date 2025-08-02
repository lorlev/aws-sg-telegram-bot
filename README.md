# 🔐 Telegram AWS Security Group Access Bot

This bot allows users to request temporary access to AWS Security Groups via Telegram.

- **MySQL (port 3306)** — available to everyone.
- **SSH (port 22)** — only allowed for a specific telegram user.
- Access is auto-removed after a defined time (default 48 hours, configurable).
- IPs and timestamps are stored in the AWS SG rule `Description` in a compact format.

---

## 🚀 Features

- `/give_me_access <ip>` — opens access to the caller's IP.
- Automatically cleans up old IPs before adding a new one.
- IPs are annotated with `bot=true;u=username;dt=timestamp`.
- Uses `boto3` + `python-telegram-bot` for a clean AWS + Telegram integration.
- Access logic is enforced per-user (SSH is only granted to AUTHORIZED_SSH_USER_ID).

---

## 📦 Requirements

- Python 3.10+
- AWS account with access to EC2 Security Groups
- Telegram account
- Git, curl, unzip (for CLI installation)

---

## 🛠 Setup Instructions

### 1️⃣ Register Your Telegram Bot

1. Open Telegram and search `@BotFather`.
2. Send `/newbot`
3. Provide:
   - A name (e.g. `AccessBot`)
   - A username (must end in `bot`, e.g. `awsaccess_bot`)
4. Copy the **bot token** — you'll use it in your `.env`.

---

### 2️⃣ Create an IAM User in AWS

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Click **Users → Add user**
3. Set:
   - **Username**: `telegram-bot`
   - ✅ Enable *Programmatic access*
4. Attach this **custom inline policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    }
  ]
}
```

5. Save the **Access Key ID** and **Secret Access Key** — you'll need them.

---

### 3️⃣ Clone the Bot Repository

```bash
git clone https://github.com/lorlev/aws-sg-telegram-bot.git
cd telegram-sg-bot
```

---

### 4️⃣ Create `.env` File

```bash
cp .env.example .env
nano .env
```

Fill in:

```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=your_aws_region
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

---

### 5️⃣ Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 6️⃣ Run the Bot

```bash
python access.bot.py
```

---

## 🔐 Access Rules (by design)

| Port | Service | SG ID                    | Who Can Access?                   |
|------|---------|--------------------------|-----------------------------------|
| 22   | SSH     | `sg-0dbc33db0b67834e7`   | Only Telegram user ID `123456789` |
| 3306 | MySQL   | `sg-062a6f4561d354465`   | Anyone via bot                    |

The bot enforces this logic in Python — IPs added to SG are tagged with:

```text
bot=true;u=John;dt=2025-08-02T14-40-00
```

---

## ⚙️ Deploy with systemd (optional)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/accessbot.service
```

Paste:

```ini
[Unit]
Description=Telegram Access Bot
After=network.target

[Service]
WorkingDirectory=/path/to/telegram-sg-bot
ExecStart=/path/to/telegram-sg-bot/venv/bin/python access.bot.py
Restart=always
EnvironmentFile=/path/to/telegram-sg-bot/.env

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable accessbot
sudo systemctl start accessbot
```

---

## 📁 File Overview

```plaintext
telegram-sg-bot/
├── access.bot.py         # Main bot logic
├── .env.example          # Sample config
├── requirements.txt      # Python dependencies
├── .gitignore            # Files to exclude from Git
└── README.md             # This file
```

---

## 🛡 Security Tips

- Store `.env` securely — never commit it!
- Rotate AWS credentials regularly.
- Use IAM roles if deploying on EC2 (no hardcoded creds).
- Use GitHub secrets if deploying via GitHub Actions or CI/CD.

---

## 📄 License

GNU GENERAL PUBLIC License
