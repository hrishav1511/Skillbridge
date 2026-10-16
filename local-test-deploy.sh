#!/usr/bin/env bash
set -euo pipefail

# Load local environment variables automatically
if [ -f ".env.local" ]; then
  set -a
  source .env.local
  set +a
else
  echo ".env.local not found in project root."
  exit 1
fi

# AWS CLI often reads AWS_DEFAULT_REGION
export AWS_DEFAULT_REGION="${AWS_REGION:-}"

required_vars=(
  AWS_REGION
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  EC2_USER
  EC2_DEPLOY_PATH
  EC2_KEY_NAME
  EC2_SECURITY_GROUP_NAME
  EC2_INSTANCE_NAME
  EC2_INSTANCE_TYPE
  EC2_PRIVATE_KEY_PATH
  EC2_PUBLIC_KEY_PATH
)

echo "Checking required variables..."
for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "Missing required variable: $var"
    exit 1
  fi
done

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is not installed or not in PATH."
  echo "Install AWS CLI v2, then reopen Git Bash."
  exit 1
fi

if [ ! -f "$EC2_PRIVATE_KEY_PATH" ]; then
  echo "Private key not found: $EC2_PRIVATE_KEY_PATH"
  exit 1
fi

if [ ! -f "$EC2_PUBLIC_KEY_PATH" ]; then
  echo "Public key not found: $EC2_PUBLIC_KEY_PATH"
  exit 1
fi

chmod 600 "$EC2_PRIVATE_KEY_PATH"

echo "Testing AWS credentials..."
aws sts get-caller-identity

echo "Preparing deploy artifact..."
rm -rf deploy deploy.tar.gz
mkdir -p deploy
cp -r team-pages/* deploy/
cp team-pages/about_page.html deploy/index.html
tar -czf deploy.tar.gz -C deploy .

echo "Importing EC2 key pair if missing..."
if aws ec2 describe-key-pairs --key-names "$EC2_KEY_NAME" >/dev/null 2>&1; then
  echo "Key pair already exists: $EC2_KEY_NAME"
else
  aws ec2 import-key-pair \
    --key-name "$EC2_KEY_NAME" \
    --public-key-material fileb://"$EC2_PUBLIC_KEY_PATH"

  echo "Imported key pair: $EC2_KEY_NAME"
fi

echo "Finding default VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
  echo "No default VPC found in region $AWS_REGION."
  exit 1
fi

echo "Using VPC: $VPC_ID"

echo "Creating/finding security group..."
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=$EC2_SECURITY_GROUP_NAME" "Name=vpc-id,Values=$VPC_ID" \
  --query "SecurityGroups[0].GroupId" \
  --output text)

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  SG_ID=$(aws ec2 create-security-group \
    --group-name "$EC2_SECURITY_GROUP_NAME" \
    --description "Security group for SkillBridge EC2 web server" \
    --vpc-id "$VPC_ID" \
    --query "GroupId" \
    --output text)

  echo "Created security group: $SG_ID"
else
  echo "Security group already exists: $SG_ID"
fi

echo "Opening ports 22 and 80..."
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 || true

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 || true

echo "Finding latest Ubuntu 24.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters \
    "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
    "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)

if [ "$AMI_ID" = "None" ] || [ -z "$AMI_ID" ]; then
  echo "Could not find Ubuntu AMI."
  exit 1
fi

echo "Using AMI: $AMI_ID"

echo "Finding existing EC2 instance..."
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters \
    "Name=tag:Name,Values=$EC2_INSTANCE_NAME" \
    "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)

if [ "$INSTANCE_ID" = "None" ] || [ -z "$INSTANCE_ID" ]; then
  echo "Creating EC2 instance..."

  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$EC2_INSTANCE_TYPE" \
    --key-name "$EC2_KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_INSTANCE_NAME}]" \
    --query "Instances[0].InstanceId" \
    --output text)

  echo "Created instance: $INSTANCE_ID"
else
  echo "Found existing instance: $INSTANCE_ID"
fi

STATE=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].State.Name" \
  --output text)

echo "Current instance state: $STATE"

if [ "$STATE" = "stopped" ]; then
  echo "Starting stopped instance..."
  aws ec2 start-instances --instance-ids "$INSTANCE_ID"
fi

echo "Waiting for EC2 instance to be running and healthy..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID"

EC2_HOST=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

if [ "$EC2_HOST" = "None" ] || [ -z "$EC2_HOST" ]; then
  echo "EC2 public IP not found."
  exit 1
fi

echo "EC2 public IP: $EC2_HOST"

echo "Waiting for SSH..."
mkdir -p ~/.ssh

for i in {1..30}; do
  if ssh-keyscan -T 5 -H "$EC2_HOST" >> ~/.ssh/known_hosts 2>/dev/null; then
    echo "SSH is ready."
    break
  fi

  echo "SSH not ready yet. Attempt $i/30"
  sleep 10
done

ssh-keyscan -T 10 -H "$EC2_HOST" >> ~/.ssh/known_hosts

echo "Testing SSH connection..."
ssh -i "$EC2_PRIVATE_KEY_PATH" "$EC2_USER@$EC2_HOST" "echo SSH connection successful"

echo "Installing/configuring Nginx..."
ssh -i "$EC2_PRIVATE_KEY_PATH" "$EC2_USER@$EC2_HOST" <<'REMOTE_NGINX'
  set -e
  sudo apt-get update
  sudo apt-get install -y nginx

  sudo mkdir -p /var/www/about-page

  sudo tee /etc/nginx/sites-available/about-page > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    root /var/www/about-page;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

  sudo ln -sf /etc/nginx/sites-available/about-page /etc/nginx/sites-enabled/about-page
  sudo rm -f /etc/nginx/sites-enabled/default

  sudo nginx -t
  sudo systemctl enable nginx
  sudo systemctl restart nginx
REMOTE_NGINX

echo "Uploading files..."
scp -i "$EC2_PRIVATE_KEY_PATH" deploy.tar.gz "$EC2_USER@$EC2_HOST:/tmp/deploy.tar.gz"

echo "Deploying files..."
ssh -i "$EC2_PRIVATE_KEY_PATH" "$EC2_USER@$EC2_HOST" <<REMOTE_DEPLOY
  set -e
  sudo mkdir -p "$EC2_DEPLOY_PATH"
  sudo rm -rf "$EC2_DEPLOY_PATH"/*
  sudo tar -xzf /tmp/deploy.tar.gz -C "$EC2_DEPLOY_PATH"
  sudo chown -R www-data:www-data "$EC2_DEPLOY_PATH"
  rm /tmp/deploy.tar.gz
  sudo systemctl reload nginx
REMOTE_DEPLOY

echo ""
echo "Deployment complete."
echo "Website URL: http://$EC2_HOST"
echo "Instance ID: $INSTANCE_ID"
