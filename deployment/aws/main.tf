# ==============================================================================
# Terraform Configuration for RAGMultiAgent EC2 Deployment
# ==============================================================================
# This creates all AWS resources needed for the thought processor application
# 
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
# ==============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Optional: Store state in S3
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "ragmultiagent/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "RAGMultiAgent"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ==============================================================================
# Variables
# ==============================================================================

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.large"  # 2 vCPU, 8GB RAM
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Change this to your IP!
}

variable "domain_name" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "enable_monitoring" {
  description = "Enable CloudWatch detailed monitoring"
  type        = bool
  default     = true
}

variable "volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 50
}

# ==============================================================================
# Data Sources
# ==============================================================================

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get latest Ubuntu 22.04 LTS AMI (alternative)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ==============================================================================
# VPC and Networking
# ==============================================================================

# Create VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "ragmultiagent-vpc-${var.environment}"
  }
}

# Create Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "ragmultiagent-igw-${var.environment}"
  }
}

# Create Public Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "ragmultiagent-public-subnet-${var.environment}"
  }
}

# Create Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "ragmultiagent-public-rt-${var.environment}"
  }
}

# Associate Route Table with Subnet
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ==============================================================================
# Security Groups
# ==============================================================================

# Application Security Group
resource "aws_security_group" "app" {
  name        = "ragmultiagent-app-sg-${var.environment}"
  description = "Security group for RAGMultiAgent application"
  vpc_id      = aws_vpc.main.id
  
  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
    description = "SSH access"
  }
  
  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }
  
  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }
  
  # API access
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "API access"
  }
  
  # Frontend access
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Frontend access"
  }
  
  # Grafana (if monitoring enabled)
  ingress {
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
    description = "Grafana monitoring"
  }
  
  # Prometheus (if monitoring enabled)
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
    description = "Prometheus metrics"
  }
  
  # Egress - Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }
  
  tags = {
    Name = "ragmultiagent-app-sg-${var.environment}"
  }
}

# ==============================================================================
# IAM Role and Instance Profile
# ==============================================================================

# IAM Role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "ragmultiagent-ec2-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "ragmultiagent-ec2-role-${var.environment}"
  }
}

# Attach CloudWatch policy
resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Attach SSM policy (for Session Manager)
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Custom policy for Secrets Manager (for API keys)
resource "aws_iam_role_policy" "secrets" {
  name = "ragmultiagent-secrets-policy"
  role = aws_iam_role.ec2_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:ragmultiagent/*"
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ragmultiagent-ec2-profile-${var.environment}"
  role = aws_iam_role.ec2_role.name
}

# ==============================================================================
# EC2 Instance
# ==============================================================================

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2.id  # or data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  
  monitoring = var.enable_monitoring
  
  root_block_device {
    volume_size           = var.volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = false  # Keep data even if instance is terminated
    
    tags = {
      Name = "ragmultiagent-root-volume-${var.environment}"
    }
  }
  
  user_data = file("${path.module}/user-data.sh")
  
  tags = {
    Name = "ragmultiagent-app-${var.environment}"
  }
  
  lifecycle {
    ignore_changes = [ami]  # Don't recreate if AMI updates
  }
}

# ==============================================================================
# Elastic IP (Optional but Recommended)
# ==============================================================================

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  
  tags = {
    Name = "ragmultiagent-eip-${var.environment}"
  }
  
  depends_on = [aws_internet_gateway.main]
}

# ==============================================================================
# CloudWatch Alarms (Optional)
# ==============================================================================

resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "ragmultiagent-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  
  dimensions = {
    InstanceId = aws_instance.app.id
  }
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "ragmultiagent-status-check-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors EC2 status checks"
  
  dimensions = {
    InstanceId = aws_instance.app.id
  }
}

# ==============================================================================
# Outputs
# ==============================================================================

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "Public IP address"
  value       = aws_eip.app.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name"
  value       = aws_instance.app.public_dns
}

output "api_url" {
  description = "API endpoint URL"
  value       = "http://${aws_eip.app.public_ip}:8000"
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "http://${aws_eip.app.public_ip}:3000"
}

output "grafana_url" {
  description = "Grafana monitoring URL"
  value       = "http://${aws_eip.app.public_ip}:3001"
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i /path/to/${var.key_name}.pem ec2-user@${aws_eip.app.public_ip}"
}
