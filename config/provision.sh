#!/bin/bash -eux

set_locale() {
  LOCALE="en_GB.UTF-8"
  locale-gen ${LOCALE}
  update-locale
}

update_package_index() {
    sudo apt-get update
}

install_required_packages() {
    sudo apt-get install -y \
	ack-grep \
        dos2unix \
	git \
	htop \
	make \
	ruby-sass \
	run-one \
	tree \
	unzip \
	virtualenv \
	whois \
	xclip \
	zip
}

configure_ack() {
    sudo dpkg-divert --local --divert /usr/bin/ack --rename --add /usr/bin/ack-grep
}

disable_ubuntu_motd() {
  # This is absurd, but to switch off the message-of-the-day *framework*
  # you have to comment out some lines in a pam module!!
  # http://ubuntuforums.org/showthread.php?t=1449020

  sed -e '/pam_motd.so/ s/^#*/#/' -i /etc/pam.d/sshd
}

install_symlinks() {
    ln -sf /vagrant/config/bashrc /home/vagrant/.bashrc
    ln -sf /vagrant/config/my.cnf /home/vagrant/.my.cnf
    ln -sf /vagrant/config/go_paths.sh /etc/profile.d/go_paths.sh
}

atomic_download() {
    URL=$1
    DEST=$2

    if [ ! -f "$DEST" ]; then
      TMP="$(tempfile)"
      wget -qO "${TMP}" "${URL}" && mv "${TMP}" "${DEST}"
    fi
}

install_go_1_10() {
  if [ ! -f "/usr/local/go/bin/go" ]; then
    FILENAME="go1.10.1.linux-amd64.tar.gz"

    atomic_download https://dl.google.com/go/${FILENAME} /tmp/${FILENAME}

    tar --directory /usr/local -xzf /tmp/${FILENAME}
  fi
}

install_mysql() {
  # Avoid being prompted for the root password
  echo "mysql-server-5.7 mysql-server/root_password password Jp3pZgXdnztvrTmjfi" | debconf-set-selections
  echo "mysql-server-5.7 mysql-server/root_password_again password Jp3pZgXdnztvrTmjfi" | debconf-set-selections
  apt install -y mysql-server-5.7
}

load_go_paths() {
  . /vagrant/config/go_paths.sh
}

install_trillian_from_if_fork_master() {
  # Go get: https://golang.org/cmd/go/#hdr-Download_and_install_packages_and_dependencies

  run_as_vagrant "go get github.com/projectsbyif/trillian"
  run_as_vagrant "cd $GOPATH/src/github.com/projectsbyif/trillian && go get -t -u -v ./..."
}

build_trillian_createtree() {
  run_as_vagrant "cd $GOPATH/src/github.com/projectsbyif/trillian && go build ./cmd/createtree"
}

build_and_run_trillian_tests() {
  run_as_vagrant "cd $GOPATH/src/github.com/projectsbyif/trillian && go test ./..."
}

run_trillian_log_integration_tests() {
  run_as_vagrant "cd $GOPATH/src/github.com/projectsbyif/trillian && ./integration/log_integration_test.sh"
}

run_as_vagrant() {
  su vagrant bash -l -c "$1"
}


set_locale
disable_ubuntu_motd
install_symlinks
update_package_index
install_required_packages
# configure_ack

install_mysql
install_go_1_10
load_go_paths

install_trillian_from_if_fork_master
build_trillian_createtree

# set +e
# build_and_run_trillian_tests
# set -e
#
# run_trillian_log_integration_tests

echo "OK, done."
