Here's how to setup the platform by hand.

https://docs.docker.com/installation/ubuntulinux/

apt-get update
apt-get install -y linux-image-generic-lts-raring linux-headers-generic-lts-raring
apt-get install -y --install-recommends linux-generic-lts-raring xserver-xorg-lts-raring lib
reboot
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
curl -sSL https://get.docker.com/ubuntu/ | sudo sh
