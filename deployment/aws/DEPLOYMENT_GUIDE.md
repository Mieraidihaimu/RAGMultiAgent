# AWS EC2 Deployment Guide

## Overview

This guide walks you through deploying the RAGMultiAgent Thought Processor application on AWS EC2.

## Prerequisites

### Local Machine
- AWS CLI installed and configured
- Terraform >= 1.0
- SSH client
- Your AWS credentials configured (`aws configure`)

### AWS Account
- Active AWS account
- IAM permissions to create EC2, VPC, Security Groups, IAM roles
- SSH key pair created in AWS EC2 console

## Architecture

The deployment creates:
- **VPC** with public subnet
- **EC2 instance** (t3.large recommended) running Docker
- **Security Groups** for controlled access
- **Elastic IP** for stable addressing
- **IAM Role** with necessary permissions
- **CloudWatch** monitoring and alarms

## Quick Start

### 1. Prepare SSH Key

Create an SSH key pair in AWS EC2 console:
```bash
# In AWS Console: EC2 > Key Pairs > Create Key Pair
# Download the .pem file and secure it
chmod 400 ~/path/to/your-key.pem
```

### 2. Configure Terraform

```bash
cd deployment/aws

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
vim terraform.tfvars
```

Required changes in `terraform.tfvars`:
```hcl
key_name         = "your-key-name"           # Your SSH key name
allowed_ssh_cidr = ["YOUR.IP.ADDRESS/32"]    # Your IP address
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply (create resources)
terraform apply
```

This will output:
- Instance ID
- Public IP address
- SSH command
- API and Frontend URLs

### 4. Connect to Instance

```bash
# SSH into your instance
ssh -i ~/path/to/your-key.pem ec2-user@<PUBLIC_IP>
```

### 5. Deploy Application

On the EC2 instance:

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/YOUR-USERNAME/RAGMultiAgent.git ragmultiagent
cd ragmultiagent

# Create environment file
cp .env.example .env

# Edit .env with your configuration
sudo vim .env
```

Required environment variables:
```bash
# AI API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Database
POSTGRES_PASSWORD=strong_password_here

# Security
JWT_SECRET_KEY=generate_random_secret_here

# Optional: Use AWS Secrets Manager
# AWS_SECRETS_ENABLED=true
```

### 6. Start Services

```bash
# Start all services
sudo docker-compose up -d

# Check status
sudo docker-compose ps

# View logs
sudo docker-compose logs -f api
```

### 7. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check services
sudo docker-compose ps
```

Access your application:
- **API**: `http://<PUBLIC_IP>:8000`
- **Frontend**: `http://<PUBLIC_IP>:3000`
- **API Docs**: `http://<PUBLIC_IP>:8000/docs`

## Instance Types

### Recommended Configurations

| Instance Type | vCPU | RAM   | Use Case              | Cost/month* |
|---------------|------|-------|-----------------------|-------------|
| t3.large      | 2    | 8 GB  | Production (minimal)  | ~$60        |
| t3.xlarge     | 4    | 16 GB | Production (standard) | ~$120       |
| t3.2xlarge    | 8    | 32 GB | Production (heavy)    | ~$240       |
| r6i.large     | 2    | 16 GB | Memory-intensive      | ~$120       |

*Approximate costs for us-east-1 region

### Minimum Requirements
- **2 vCPU**
- **8GB RAM**
- **50GB Storage**

## Security Best Practices

### 1. Restrict SSH Access

In `terraform.tfvars`:
```hcl
allowed_ssh_cidr = ["YOUR.IP.ADDRESS/32"]  # Not 0.0.0.0/0!
```

### 2. Use AWS Secrets Manager

Store sensitive data in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
    --name ragmultiagent/api-keys \
    --secret-string '{
        "ANTHROPIC_API_KEY":"your_key",
        "OPENAI_API_KEY":"your_key",
        "GOOGLE_API_KEY":"your_key"
    }'
```

Update your application to fetch from Secrets Manager.

### 3. Enable HTTPS

#### Option A: Use AWS Application Load Balancer

```bash
# Create ALB with ACM certificate
# Configure SSL/TLS termination
```

#### Option B: Use Nginx Reverse Proxy with Let's Encrypt

```bash
# On EC2 instance
sudo yum install -y certbot
sudo certbot --nginx -d yourdomain.com
```

### 4. Regular Updates

```bash
# Schedule automated security updates
sudo yum install -y yum-cron
sudo systemctl enable yum-cron
sudo systemctl start yum-cron
```

## Monitoring

### CloudWatch Alarms

The Terraform configuration creates:
- CPU utilization alarm (>80%)
- Status check alarm

### View Metrics

```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=<INSTANCE_ID> \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average
```

### Application Monitoring

Enable Grafana (included in docker-compose):
```bash
# Start with monitoring profile
sudo docker-compose --profile monitoring up -d

# Access Grafana
# http://<PUBLIC_IP>:3001
# Default: admin/admin
```

## Backup and Recovery

### 1. Database Backups

```bash
# Automated daily backups (cron job)
crontab -e

# Add this line (runs at 2 AM daily)
0 2 * * * cd /opt/ragmultiagent && docker-compose exec -T db pg_dump -U thoughtprocessor thoughtprocessor | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### 2. EBS Snapshots

```bash
# Create snapshot via AWS CLI
aws ec2 create-snapshot \
    --volume-id <VOLUME_ID> \
    --description "RAGMultiAgent backup $(date)"

# Or use AWS Backup service
```

### 3. Application State

```bash
# Backup docker volumes
sudo docker-compose down
sudo tar -czf /backups/volumes_$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/
sudo docker-compose up -d
```

## Scaling

### Vertical Scaling (Resize Instance)

```bash
# Stop instance
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# Change instance type
aws ec2 modify-instance-attribute \
    --instance-id <INSTANCE_ID> \
    --instance-type t3.xlarge

# Start instance
aws ec2 start-instances --instance-ids <INSTANCE_ID>
```

### Horizontal Scaling

For high availability:
1. Use Auto Scaling Group
2. Add Application Load Balancer
3. Use RDS instead of containerized PostgreSQL
4. Use ElastiCache for Redis
5. Use Amazon MSK for Kafka

## Troubleshooting

### Instance Not Accessible

```bash
# Check instance status
aws ec2 describe-instance-status --instance-ids <INSTANCE_ID>

# View system log
aws ec2 get-console-output --instance-id <INSTANCE_ID>

# Connect via Session Manager (no SSH needed)
aws ssm start-session --target <INSTANCE_ID>
```

### Docker Issues

```bash
# SSH into instance
ssh -i key.pem ec2-user@<PUBLIC_IP>

# Check Docker status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check containers
sudo docker-compose ps

# View logs
sudo docker-compose logs --tail=100
```

### High Memory Usage

```bash
# Check memory
free -h

# Find memory hogs
docker stats

# Restart specific service
sudo docker-compose restart api
```

### Database Connection Issues

```bash
# Check database container
sudo docker-compose logs db

# Connect to database
sudo docker-compose exec db psql -U thoughtprocessor

# Check connections
SELECT * FROM pg_stat_activity;
```

## Cost Optimization

### 1. Use Reserved Instances

For long-term deployments:
- Save up to 72% vs On-Demand
- 1-year or 3-year commitment

### 2. Spot Instances

For development/testing:
```hcl
# In main.tf
resource "aws_spot_instance_request" "app" {
  # ... configuration
}
```

### 3. Auto-Stop Development Instances

```bash
# Create Lambda function to stop instances at night
# Schedule via EventBridge
```

### 4. Use AWS Free Tier

- t2.micro free for first 12 months
- 30GB EBS storage free
- Good for testing

## Maintenance

### Regular Tasks

#### Daily
- Monitor logs
- Check CloudWatch alarms

#### Weekly
- Review security groups
- Check for updates

#### Monthly
- Review costs
- Update Docker images
- Patch OS

### Update Application

```bash
# SSH to instance
cd /opt/ragmultiagent

# Pull latest code
git pull

# Rebuild and restart
sudo docker-compose down
sudo docker-compose build
sudo docker-compose up -d

# Check status
sudo docker-compose ps
```

## Teardown

To destroy all resources:

```bash
cd deployment/aws
terraform destroy
```

**Warning**: This will permanently delete all resources including data!

## Additional Resources

- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Documentation](https://docs.docker.com/)
- [Application Repository](https://github.com/YOUR-USERNAME/RAGMultiAgent)

## Support

For issues:
1. Check logs: `sudo docker-compose logs`
2. Review this guide's Troubleshooting section
3. Check GitHub Issues
4. Contact support

## Next Steps

After deployment:
1. ✅ Set up DNS (Route 53 or your provider)
2. ✅ Enable HTTPS/SSL
3. ✅ Configure automated backups
4. ✅ Set up monitoring alerts
5. ✅ Enable AWS Backup
6. ✅ Configure CloudWatch Logs
7. ✅ Set up CI/CD pipeline
8. ✅ Performance testing

---

**Deployment Complete! 🚀**

Your RAGMultiAgent application is now running on AWS EC2.
