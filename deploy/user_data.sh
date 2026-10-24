#!/bin/bash
# EC2 user-data for the demo box (Ubuntu 24.04, ap-south-1, instance profile pehchaan-ml-ec2).
# Installs Docker + AWS CLI and pulls the v1 voice weights with the instance role. No keys on the box.
set -euxo pipefail
exec > >(tee -a /var/log/pehchaan-bootstrap.log) 2>&1

curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
snap install aws-cli --classic

# 2 GB swap: image builds (torch wheels) on a 4 GB box
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

W=/home/ubuntu/pehchaan/deploy/weights
mkdir -p "$W"
/snap/bin/aws s3 cp --only-show-errors \
  s3://pehchaan-ml-301745146083-use1/models/pehchaan-xlsr-aasist-ft-v1/weights/pehchaan-xlsr-aasist-ft-v1.safetensors "$W/"
chown -R ubuntu:ubuntu /home/ubuntu/pehchaan
touch /home/ubuntu/.pehchaan-bootstrap-done
