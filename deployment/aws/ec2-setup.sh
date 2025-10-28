#!/bin/bash
# ==============================================================================
# EC2 Instance Setup Script for RAGMultiAgent Application
# ==============================================================================
# This script sets up a fresh EC2 instance (Amazon Linux 2 or Ubuntu) with all
# dependencies needed to run the RAGMultiAgent thought processor application.
#
# Prerequisites:
# - EC2 instance type: t3.large or larger (minimum 2 vCPU, 8GB RAM)
# - Security groups configured (see security-groups.tf)
# - SSH key pair for access
#
# Usage:
#   chmod +x ec2-setup.sh
#   sudo ./ec2-setup.sh
# ==============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS"
        exit 1
    fi
    log_info "Detected OS: $OS $VERSION"
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ]; then
        sudo yum update -y
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get update -y
        sudo apt-get upgrade -y
    fi
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_warn "Docker already installed"
        return 0
    fi
    
    if [ "$OS" = "amzn" ]; then
        # Amazon Linux 2
        sudo yum install -y docker
        sudo service docker start
        sudo usermod -a -G docker ec2-user
    elif [ "$OS" = "ubuntu" ]; then
        # Ubuntu
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Set up stable repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        sudo apt-get update -y
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker ubuntu
    fi
    
    log_info "Docker installed successfully"
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_warn "Docker Compose already installed"
        return 0
    fi
    
    # Install latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_info "Docker Compose installed successfully"
}

# Install Git
install_git() {
    log_info "Installing Git..."
    
    if command -v git &> /dev/null; then
        log_warn "Git already installed"
        return 0
    fi
    
    if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ]; then
        sudo yum install -y git
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get install -y git
    fi
}

# Install Python 3.11
install_python() {
    log_info "Installing Python 3.11..."
    
    if [ "$OS" = "amzn" ]; then
        sudo yum install -y python3.11 python3.11-pip
    elif [ "$OS" = "ubuntu" ]; then
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update -y
        sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
    fi
    
    # Create symlinks
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    sudo update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
}

# Install Node.js (for frontend if needed)
install_nodejs() {
    log_info "Installing Node.js..."
    
    if command -v node &> /dev/null; then
        log_warn "Node.js already installed"
        return 0
    fi
    
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo yum install -y nodejs || sudo apt-get install -y nodejs
}

# Install essential tools
install_tools() {
    log_info "Installing essential tools..."
    
    if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ]; then
        sudo yum install -y \
            vim \
            htop \
            wget \
            curl \
            unzip \
            jq \
            nc \
            telnet
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get install -y \
            vim \
            htop \
            wget \
            curl \
            unzip \
            jq \
            netcat \
            telnet
    fi
}

# Setup application directory
setup_app_directory() {
    log_info "Setting up application directory..."
    
    APP_DIR="/opt/ragmultiagent"
    sudo mkdir -p $APP_DIR
    sudo chown -R $USER:$USER $APP_DIR
    
    log_info "Application directory created at $APP_DIR"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    if [ "$OS" = "amzn" ]; then
        # Configure iptables for Amazon Linux
        sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT    # SSH
        sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT    # HTTP
        sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT   # HTTPS
        sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT  # API
        sudo iptables -A INPUT -p tcp --dport 3000 -j ACCEPT  # Frontend
        sudo service iptables save
    elif [ "$OS" = "ubuntu" ]; then
        # Configure UFW for Ubuntu
        sudo ufw allow 22/tcp   # SSH
        sudo ufw allow 80/tcp   # HTTP
        sudo ufw allow 443/tcp  # HTTPS
        sudo ufw allow 8000/tcp # API
        sudo ufw allow 3000/tcp # Frontend
        sudo ufw --force enable
    fi
}

# Setup swap (for smaller instances)
setup_swap() {
    log_info "Setting up swap space..."
    
    # Check if swap already exists
    if sudo swapon --show | grep -q "/swapfile"; then
        log_warn "Swap already configured"
        return 0
    fi
    
    # Create 4GB swap file
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    
    # Make swap permanent
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    
    log_info "Swap configured successfully"
}

# Setup CloudWatch agent (optional)
setup_cloudwatch() {
    log_info "Setting up CloudWatch agent..."
    
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    sudo rpm -U ./amazon-cloudwatch-agent.rpm || \
        sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
    rm -f amazon-cloudwatch-agent.*
    
    log_info "CloudWatch agent installed (configuration needed)"
}

# Create systemd service for Docker Compose
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat << 'EOF' | sudo tee /etc/systemd/system/ragmultiagent.service
[Unit]
Description=RAG Multi-Agent Thought Processor
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ragmultiagent
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable ragmultiagent.service
    
    log_info "Systemd service created"
}

# Setup log rotation
setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    cat << 'EOF' | sudo tee /etc/logrotate.d/ragmultiagent
/opt/ragmultiagent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ec2-user ec2-user
    sharedscripts
    postrotate
        /usr/local/bin/docker-compose -f /opt/ragmultiagent/docker-compose.yml restart api > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

# Main installation flow
main() {
    log_info "Starting EC2 setup for RAGMultiAgent..."
    
    detect_os
    update_system
    install_docker
    install_docker_compose
    install_git
    install_python
    install_nodejs
    install_tools
    setup_app_directory
    configure_firewall
    setup_swap
    create_systemd_service
    setup_log_rotation
    
    # Optional
    # setup_cloudwatch
    
    log_info "EC2 setup completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Clone your repository to /opt/ragmultiagent"
    log_info "2. Copy .env.example to .env and configure"
    log_info "3. Run: cd /opt/ragmultiagent && sudo docker-compose up -d"
    log_info "4. Check status: sudo docker-compose ps"
    log_info ""
    log_info "Note: You may need to log out and back in for Docker permissions to take effect"
}

# Run main function
main "$@"
