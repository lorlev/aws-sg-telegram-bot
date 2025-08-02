import os
import ipaddress
import boto3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS config
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'eu-central-1')
ec2 = boto3.client('ec2', region_name=AWS_REGION)

# Security Groups
MYSQL_SG = 'your_aws_mysql_sg'
SSH_SG = 'your_aws_ssh_sg'

# Telegram Users
AUTHORIZED_SSH_USER_ID = 'telegram_user_id'

# --- Helpers ---
def is_valid_ipv4(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def check_ip_in_sg(security_group_id, ip, port):
    response = ec2.describe_security_groups(GroupIds=[security_group_id])
    for perm in response['SecurityGroups'][0]['IpPermissions']:
        if perm.get('FromPort') == port and perm.get('ToPort') == port and perm.get('IpProtocol') == 'tcp':
            for cidr in perm.get('IpRanges', []):
                if cidr['CidrIp'] == f'{ip}/32':
                    return True
    return False

def cleanup_expired_ips_for_group(sg_id, port):
    try:
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=48)

        response = ec2.describe_security_groups(GroupIds=[sg_id])
        permissions = response['SecurityGroups'][0]['IpPermissions']
        to_revoke = []

        for perm in permissions:
            if perm.get('FromPort') != port or perm.get('IpProtocol') != 'tcp':
                continue

            for ip_range in perm.get('IpRanges', []):
                cidr = ip_range.get('CidrIp')
                desc = ip_range.get('Description', '')

                try:
                    if "bot=true" in desc:
                        parts = dict(item.split("=") for item in desc.split(";") if "=" in item)
                        dt_raw = parts.get("dt")
                        if dt_raw:
                            added_time = datetime.strptime(dt_raw, "%Y-%m-%dT%H-%M-%S")
                            if added_time < cutoff:
                                to_revoke.append({'CidrIp': cidr})
                except Exception:
                    continue  # Skip malformed entries

        if to_revoke:
            ec2.revoke_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'FromPort': port,
                    'ToPort': port,
                    'IpProtocol': 'tcp',
                    'IpRanges': to_revoke
                }]
            )
    except Exception as e:
        print(f"Cleanup error for {sg_id}: {e}")

def authorize_ip(security_group_id, ip, port, username):
    cleanup_expired_ips_for_group(security_group_id, port)

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    description = f"bot=true;u={username};dt={timestamp}"[:255]

    ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'FromPort': port,
                'ToPort': port,
                'IpProtocol': 'tcp',
                'IpRanges': [
                    {
                        'CidrIp': f'{ip}/32',
                        'Description': description
                    }
                ]
            }
        ]
    )

# --- Telegram Handler ---
async def give_me_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "user"

    if not context.args:
        await update.message.reply_text("ℹ️ Please provide an IP address.")
        return

    ip = context.args[0]
    if not is_valid_ipv4(ip):
        await update.message.reply_text("❌ Invalid IP format.")
        return

    # SSH (port 22)
    if user_id == AUTHORIZED_SSH_USER_ID:
        if not check_ip_in_sg(SSH_SG, ip, 22):
            try:
                authorize_ip(SSH_SG, ip, 22, username)
                await update.message.reply_text("✅ SSH (port 22) access granted.")
            except Exception as e:
                await update.message.reply_text(f"⚠️ SSH error: {e}")
        else:
            await update.message.reply_text("ℹ️ SSH access already exists.")
    else:
        await update.message.reply_text("⛔ SSH access is only allowed for specific user.")

    # MySQL (port 3306): Everyone
    if not check_ip_in_sg(MYSQL_SG, ip, 3306):
        try:
            authorize_ip(MYSQL_SG, ip, 3306, username)
            await update.message.reply_text("✅ MySQL (port 3306) access granted.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ MySQL error: {e}")
    else:
        await update.message.reply_text("ℹ️ MySQL access already exists.")

# --- Main Bot Setup ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("give_me_access", give_me_access))
    app.run_polling()