#!/bin/bash
# Pehchaan ML box bootstrap (runs once at first boot as root via cloud-init).
# 1) idle watchdog: shutdown -h (stop, because InstanceInitiatedShutdownBehavior=stop)
#    when all GPUs < 5% util AND no user python/ffmpeg/pip processes for 45 minutes.
# 2) instance-store NVMe -> /scratch (RAID0), re-created on every boot (data there is ephemeral).
set -euxo pipefail

mkdir -p /opt/pehchaan
cat > /opt/pehchaan/idle_watchdog.sh <<'EOF'
#!/bin/bash
# Called every minute by cron. Keeps a counter of consecutive idle minutes.
STATE=/var/lib/pehchaan_idle_minutes
LOG=/var/log/pehchaan_watchdog.log
LIMIT=${PEHCHAAN_IDLE_LIMIT_MIN:-45}
[ -f /opt/pehchaan/watchdog_disabled ] && { echo 0 > "$STATE"; exit 0; }
max_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | sort -n | tail -1)
max_util=${max_util:-0}
# user workload processes (system daemons such as networkd-dispatcher are python too, so restrict to user ubuntu)
busy_procs=$(pgrep -u ubuntu -f 'python|ffmpeg|pip|conda|aria2c|wget|git-lfs|huggingface-cli|hf ' | wc -l)
n=$(cat "$STATE" 2>/dev/null || echo 0)
if [ "$max_util" -lt 5 ] && [ "$busy_procs" -eq 0 ]; then
  n=$((n+1))
else
  n=0
fi
echo "$n" > "$STATE"
echo "$(date -Is) gpu_max=${max_util}% procs=${busy_procs} idle_min=${n}" >> "$LOG"
if [ "$n" -ge "$LIMIT" ]; then
  echo "$(date -Is) idle ${n} min >= ${LIMIT}: shutting down (instance will STOP)" >> "$LOG"
  echo 0 > "$STATE"
  /sbin/shutdown -h now
fi
EOF
chmod +x /opt/pehchaan/idle_watchdog.sh
echo 0 > /var/lib/pehchaan_idle_minutes
echo '* * * * * root /opt/pehchaan/idle_watchdog.sh' > /etc/cron.d/pehchaan-idle-watchdog
chmod 644 /etc/cron.d/pehchaan-idle-watchdog

cat > /opt/pehchaan/mount_scratch.sh <<'EOF'
#!/bin/bash
# Assemble all instance-store NVMe disks into RAID0 at /scratch (ephemeral).
set -x
mountpoint -q /scratch && exit 0
mkdir -p /scratch
DEVS=$(lsblk -dpno NAME,MODEL | grep -i 'Instance Storage' | awk '{print $1}')
N=$(echo "$DEVS" | grep -c nvme || true)
if [ "$N" -ge 2 ]; then
  mdadm --stop /dev/md0 2>/dev/null || true
  yes | mdadm --create /dev/md0 --level=0 --raid-devices="$N" $DEVS --force
  mkfs.ext4 -F -E nodiscard /dev/md0 && mount -o noatime /dev/md0 /scratch
elif [ "$N" -eq 1 ]; then
  mkfs.ext4 -F -E nodiscard $DEVS && mount -o noatime $DEVS /scratch
fi
chown ubuntu:ubuntu /scratch
EOF
chmod +x /opt/pehchaan/mount_scratch.sh
cat > /etc/systemd/system/pehchaan-scratch.service <<'EOF'
[Unit]
Description=Pehchaan scratch RAID0 on instance store
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/opt/pehchaan/mount_scratch.sh
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now pehchaan-scratch.service || true

apt-get update -y || true
DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg sox libsox-fmt-all libopus0 libopus-dev tmux aria2 git-lfs mdadm espeak-ng libsndfile1 jq || true
touch /opt/pehchaan/bootstrap_done
