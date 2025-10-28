# AWS EC2 Deployment Configuration

## 📁 Files Overview

| File | Description |
|------|-------------|
| **main.tf** | Main Terraform configuration for AWS infrastructure |
| **terraform.tfvars.example** | Example variables file (copy to terraform.tfvars) |
| **user-data.sh** | EC2 instance bootstrap script |
| **ec2-setup.sh** | Complete server setup script |
| **deploy.sh** | Application deployment automation |
| **docker-compose.prod.yml** | Production Docker Compose overrides |
| **nginx.conf** | Nginx reverse proxy configuration |
| **DEPLOYMENT_GUIDE.md** | Comprehensive deployment documentation |

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured (`aws configure`)
- Terraform installed
- SSH key pair in AWS

### 1. One-Command Terraform Deployment

```bash
# From project root
cd deployment/aws

# Configure your variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Edit: key_name, allowed_ssh_cidr

# Deploy infrastructure
terraform init
terraform apply
```

### 2. Connect and Deploy Application

```bash
# SSH to instance (use IP from terraform output)
ssh -i ~/.ssh/your-key.pem ec2-user@<PUBLIC_IP>

# Run setup script
curl -O https://raw.githubusercontent.com/YOUR-REPO/deployment/aws/ec2-setup.sh
chmod +x ec2-setup.sh
sudo ./ec2-setup.sh

# Clone and deploy
cd /opt
sudo git clone https://github.com/YOUR-REPO/RAGMultiAgent.git ragmultiagent
cd ragmultiagent

# Configure environment
cp .env.example .env
sudo vim .env  # Add your API keys

# Deploy with production config
sudo docker-compose -f docker-compose.yml -f deployment/aws/docker-compose.prod.yml up -d
```

### 3. Verify

```bash
# Check services
sudo docker-compose ps

# Test API
curl http://localhost:8000/health

# View logs
sudo docker-compose logs -f api
```

## 📊 Infrastructure Created

The Terraform configuration creates:

### Networking
- ✅ VPC (10.0.0.0/16)
- ✅ Public Subnet (10.0.1.0/24)
- ✅ Internet Gateway
- ✅ Route Tables
- ✅ Security Groups (SSH, HTTP, HTTPS, API)

### Compute
- ✅ EC2 Instance (t3.large by default)
- ✅ Elastic IP (static)
- ✅ 50GB EBS Volume (encrypted)

### Security
- ✅ IAM Role with necessary permissions
- ✅ Instance Profile
- ✅ Security Groups with minimal access
- ✅ CloudWatch integration

### Monitoring
- ✅ CloudWatch Alarms (CPU, Status Checks)
- ✅ CloudWatch Agent ready
- ✅ Detailed monitoring enabled

## 💰 Cost Estimate

### Monthly Costs (us-east-1)

| Resource | Type | Cost/Month |
|----------|------|------------|
| EC2 Instance | t3.large | ~$60 |
| EBS Volume | 50GB gp3 | ~$4 |
| Elastic IP | Active | $0 |
| Data Transfer | ~100GB | ~$9 |
| CloudWatch | Basic | ~$3 |
| **Total** | | **~$76/month** |

💡 **Optimization Tips:**
- Use Reserved Instances: Save up to 72%
- Stop instance during off-hours: Save 50%+
- Use Spot Instances for dev: Save up to 90%

## 🔒 Security Features

### Network Security
- VPC isolation
- Security groups with least privilege
- SSH restricted to specific IPs
- Separate inbound rules per service

### Data Security
- Encrypted EBS volumes
- Environment variables in .env (not committed)
- IAM roles instead of access keys
- Secrets Manager integration ready

### Application Security
- HTTPS via Nginx (nginx.conf provided)
- Rate limiting configured
- Security headers enabled
- Docker container isolation

## 📈 Scaling Options

### Vertical Scaling (Single Instance)
```bash
# Current: t3.large (2 vCPU, 8GB)
# Upgrade to: t3.xlarge (4 vCPU, 16GB)
terraform apply -var="instance_type=t3.xlarge"
```

### Horizontal Scaling (Multiple Instances)
For production high-availability:
1. Use Auto Scaling Groups
2. Add Application Load Balancer
3. Use managed services:
   - RDS for PostgreSQL
   - ElastiCache for Redis
   - Amazon MSK for Kafka

## 🔧 Configuration Details

### Terraform Variables

Edit `terraform.tfvars`:

```hcl
# Required
aws_region       = "us-east-1"
environment      = "production"
instance_type    = "t3.large"
key_name         = "your-ssh-key-name"
allowed_ssh_cidr = ["YOUR.IP.ADDRESS/32"]

# Optional
domain_name       = "thoughtprocessor.example.com"
enable_monitoring = true
volume_size       = 50
```

### Docker Compose Profiles

```bash
# Production (default)
docker-compose up -d

# With monitoring (Prometheus, Grafana)
docker-compose --profile monitoring up -d

# With search (Elasticsearch)
docker-compose --profile search up -d

# All services
docker-compose --profile monitoring --profile search up -d
```

### Environment Variables

Required in `.env`:
```bash
# AI APIs
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...

# Database
POSTGRES_PASSWORD=strong_password

# Security
JWT_SECRET_KEY=random_secret

# Optional
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

## 📝 Common Tasks

### Deploy Updates
```bash
cd /opt/ragmultiagent
sudo ./deployment/aws/deploy.sh
```

### View Logs
```bash
# All services
sudo docker-compose logs -f

# Specific service
sudo docker-compose logs -f api

# Last 100 lines
sudo docker-compose logs --tail=100
```

### Restart Services
```bash
# All services
sudo docker-compose restart

# Specific service
sudo docker-compose restart api
```

### Database Backup
```bash
# Manual backup
sudo docker-compose exec db pg_dump -U thoughtprocessor thoughtprocessor | \
    gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip < backup_20231028.sql.gz | \
    sudo docker-compose exec -T db psql -U thoughtprocessor thoughtprocessor
```

### Check Resource Usage
```bash
# System resources
htop

# Docker stats
sudo docker stats

# Disk usage
df -h
sudo docker system df
```

## 🐛 Troubleshooting

### Instance Won't Start
```bash
# Check Terraform
terraform plan

# View AWS console logs
aws ec2 get-console-output --instance-id i-xxxxx

# Use Session Manager (no SSH needed)
aws ssm start-session --target i-xxxxx
```

### Docker Issues
```bash
# Restart Docker
sudo systemctl restart docker

# Check Docker logs
sudo journalctl -u docker -f

# Rebuild containers
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

### Database Connection Failed
```bash
# Check database
sudo docker-compose logs db

# Connect to database
sudo docker-compose exec db psql -U thoughtprocessor

# Check connections
SELECT count(*) FROM pg_stat_activity;
```

### High CPU/Memory
```bash
# Identify resource hogs
sudo docker stats

# Scale down workers
# Edit docker-compose.yml: kafka-worker replicas
sudo docker-compose up -d --scale kafka-worker=2

# Restart specific service
sudo docker-compose restart api
```

### SSL/HTTPS Issues
```bash
# Generate self-signed cert (testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem -out ssl/cert.pem

# Use Let's Encrypt (production)
sudo certbot --nginx -d yourdomain.com
```

## 📚 Additional Resources

- [Full Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🎯 Production Checklist

Before going live:

- [ ] Update `allowed_ssh_cidr` to your IP only
- [ ] Generate strong passwords for all services
- [ ] Configure HTTPS/SSL certificate
- [ ] Set up automated backups
- [ ] Configure CloudWatch alarms
- [ ] Enable AWS Backup
- [ ] Set up monitoring dashboards
- [ ] Document recovery procedures
- [ ] Test backup restoration
- [ ] Configure log rotation
- [ ] Set up DNS records
- [ ] Enable AWS GuardDuty
- [ ] Review security groups
- [ ] Configure rate limiting
- [ ] Set up CI/CD pipeline

## 🆘 Support

For deployment issues:
1. Check [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
2. Review logs: `sudo docker-compose logs`
3. Check AWS console for instance status
4. Open GitHub issue with details

---

**Ready to deploy? Start with the Quick Start section above! 🚀**
