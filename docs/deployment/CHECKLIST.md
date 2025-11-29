# Deployment Checklist

Complete checklist for deploying the AI Thought Processor system.

## 📋 Pre-Deployment

### API Keys & Credentials
- [ ] Anthropic API key obtained
- [ ] OpenAI API key obtained
- [ ] Supabase project created (or local PostgreSQL ready)
- [ ] API keys tested and valid
- [ ] Billing limits set on AI providers

### Environment Setup
- [ ] `.env` file created from `.env.example`
- [ ] All required environment variables set
- [ ] Secrets are not committed to version control
- [ ] `.gitignore` includes `.env` and sensitive files

### Local Testing
- [ ] Docker and Docker Compose installed
- [ ] `make setup` runs successfully
- [ ] Database initializes without errors
- [ ] Sample data loads correctly
- [ ] API health check passes
- [ ] `make test-api` completes successfully
- [ ] Batch processor runs without errors
- [ ] Cache hit tracking visible in logs

## 🚀 Deployment Options

### Option 1: Local/Self-Hosted Docker

#### Initial Setup
- [ ] Server provisioned (Ubuntu 22.04+, 2GB RAM, 20GB disk)
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned to server
- [ ] `.env` configured with production values
- [ ] Firewall rules configured (ports 80, 443, 5432, 8000)

#### Deployment
```bash
- [ ] docker-compose up -d
- [ ] Database migrations applied
- [ ] Sample data removed (or user data imported)
- [ ] API accessible externally
- [ ] Cron job configured (or enabled in docker-compose)
```

#### Optional: Nginx + SSL
- [ ] Nginx installed and configured
- [ ] SSL certificate obtained (Let's Encrypt)
- [ ] Domain name configured
- [ ] HTTPS working correctly
- [ ] HTTP redirects to HTTPS

#### Verification
- [ ] API responds at public URL
- [ ] Database persistent across restarts
- [ ] Logs are being written
- [ ] Batch processor runs on schedule
- [ ] Backups configured

### Option 2: GitHub Actions (Serverless Cron)

#### Repository Setup
- [ ] Code pushed to GitHub repository
- [ ] Repository is private (recommended for security)
- [ ] `.env` and secrets NOT committed

#### Secrets Configuration
Navigate to: Repository → Settings → Secrets and variables → Actions

Add these secrets:
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `ANTHROPIC_API_KEY`
- [ ] `OPENAI_API_KEY`

#### Variables Configuration (Optional)
Add these variables if customizing:
- [ ] `CLAUDE_MODEL`
- [ ] `SEMANTIC_CACHE_THRESHOLD`
- [ ] `LOG_LEVEL`
- [ ] `RATE_LIMIT_DELAY`

#### Workflow Activation
- [ ] GitHub Actions enabled in repository
- [ ] Workflow file exists: `.github/workflows/batch-process.yml`
- [ ] Manual run tested successfully
- [ ] Scheduled runs verified in Actions tab
- [ ] Logs accessible and complete

#### Supabase Setup (Required for GitHub Actions)
- [ ] Supabase project created
- [ ] Database schema applied
- [ ] pgvector extension enabled
- [ ] Row Level Security configured (optional)
- [ ] Connection limits appropriate

#### Verification
- [ ] Workflow appears in Actions tab
- [ ] Manual trigger works
- [ ] Scheduled run executes at 2 AM UTC
- [ ] Logs show successful processing
- [ ] Database shows completed thoughts
- [ ] Cache statistics visible

### Option 3: Cloud Platform (Render/Fly.io/Railway)

#### Render Deployment

##### Prerequisites
- [ ] Render account created
- [ ] `render.yaml` configuration file created (optional)
- [ ] Repository connected to Render

##### Services Setup
**Web Service (API)**:
- [ ] Service created from Dockerfile
- [ ] Dockerfile path set to `./api/Dockerfile`
- [ ] Environment variables configured
- [ ] Health check path set to `/health`
- [ ] Auto-deploy enabled from main branch

**Cron Job (Batch Processor)**:
- [ ] Cron job created
- [ ] Schedule set to `0 2 * * *`
- [ ] Dockerfile path set to `./batch_processor/Dockerfile`
- [ ] Environment variables configured (same as API)

##### Database
- [ ] Supabase project linked OR
- [ ] Render PostgreSQL database created
- [ ] pgvector extension enabled
- [ ] Schema migrations applied
- [ ] Connection string configured in services

##### Verification
- [ ] API accessible at Render URL
- [ ] Health check passes
- [ ] Cron job runs on schedule
- [ ] Logs available in Render dashboard
- [ ] Database connections working

#### Fly.io Deployment

- [ ] Fly.io account created
- [ ] `flyctl` CLI installed
- [ ] `fly.toml` configuration created
- [ ] Secrets configured via `fly secrets set`
- [ ] App deployed with `fly deploy`
- [ ] Health checks configured
- [ ] Scaling configured (if needed)

#### Railway Deployment

- [ ] Railway account created
- [ ] GitHub repository connected
- [ ] Services created (API, Batch)
- [ ] PostgreSQL addon added OR Supabase configured
- [ ] Environment variables set
- [ ] Cron job scheduled
- [ ] Deployment successful

## 🔒 Security Checklist

### Secrets Management
- [ ] No API keys in code or commits
- [ ] `.env` in `.gitignore`
- [ ] Environment variables used for all secrets
- [ ] Different keys for dev/staging/prod
- [ ] Keys rotated regularly

### API Security
- [ ] CORS configured appropriately
- [ ] Input validation enabled (Pydantic)
- [ ] SQL injection prevention (parameterized queries)
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting considered for production

### Database Security
- [ ] Strong database password
- [ ] Database not publicly accessible (or Supabase RLS enabled)
- [ ] Regular backups configured
- [ ] SSL/TLS for database connections
- [ ] Minimal privileges for application user

### Application Security
- [ ] Dependencies up to date
- [ ] Docker images from trusted sources
- [ ] No debug mode in production
- [ ] Logs don't contain sensitive data
- [ ] Health check doesn't expose internals

## 📊 Monitoring Setup

### Logging
- [ ] Logs written to persistent storage
- [ ] Log rotation configured
- [ ] Log levels appropriate (INFO for prod)
- [ ] Error logs monitored
- [ ] Access logs retained

### Metrics
- [ ] API request count tracked
- [ ] Batch processing duration logged
- [ ] Cache hit rate monitored
- [ ] Error rate tracked
- [ ] Cost per thought calculated

### Alerts (Optional)
- [ ] Failure notifications configured
- [ ] Cost threshold alerts set
- [ ] Uptime monitoring enabled
- [ ] Database capacity alerts
- [ ] Error spike detection

### Health Checks
- [ ] API health endpoint working
- [ ] Database connectivity verified
- [ ] AI API availability checked
- [ ] Disk space monitored
- [ ] Memory usage tracked

## 💰 Cost Management

### AI API Costs
- [ ] Billing limits set on Anthropic dashboard
- [ ] Billing limits set on OpenAI dashboard
- [ ] Cost alerts configured
- [ ] Cache hit rate monitored (target: >20%)
- [ ] Prompt caching verified in logs

### Infrastructure Costs
- [ ] Free tier limits understood
- [ ] Upgrade path planned if needed
- [ ] Cost estimates validated
- [ ] Billing alerts configured

### Optimization
- [ ] Semantic cache threshold tuned (0.85-0.95)
- [ ] Prompt cache confirmed working
- [ ] Batch size appropriate
- [ ] Rate limiting prevents overage

## 🧪 Testing in Production

### Smoke Tests
```bash
- [ ] curl https://your-domain.com/health
- [ ] Create test thought via API
- [ ] Verify thought in database
- [ ] Run batch processor (manual)
- [ ] Verify completed thought
- [ ] Check cache statistics
```

### Load Testing (Optional)
- [ ] API handles expected load
- [ ] Database performance acceptable
- [ ] Batch processing completes in time
- [ ] No memory leaks observed

### Integration Tests
- [ ] End-to-end flow works
- [ ] All 5 agents execute correctly
- [ ] Results stored properly
- [ ] Weekly synthesis generates
- [ ] Error handling works

## 📚 Documentation

### User Documentation
- [ ] README.md reviewed and accurate
- [ ] QUICKSTART.md tested
- [ ] SETUP.md matches deployment
- [ ] API docs accessible
- [ ] Common issues documented

### Operational Documentation
- [ ] Runbook created for common tasks
- [ ] Backup/restore procedures documented
- [ ] Incident response plan
- [ ] Contact information updated
- [ ] Monitoring dashboards documented

### Code Documentation
- [ ] Code comments adequate
- [ ] Complex logic explained
- [ ] Environment variables documented
- [ ] API endpoints documented
- [ ] Database schema documented

## 🔄 Maintenance Plan

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check cache hit rate
- [ ] Weekly: Monitor API costs
- [ ] Monthly: Update dependencies
- [ ] Monthly: Review database size
- [ ] Quarterly: Security audit
- [ ] Quarterly: Performance review

### Backup Strategy
- [ ] Database backed up daily
- [ ] Backups tested regularly
- [ ] Retention policy defined
- [ ] Recovery procedures documented
- [ ] Off-site backups configured

### Update Strategy
- [ ] Dependency updates scheduled
- [ ] Python version upgrade plan
- [ ] Docker image updates
- [ ] Database migration strategy
- [ ] Rollback plan documented

## ✅ Final Verification

### System Health
- [ ] All services running
- [ ] No errors in logs
- [ ] API responding correctly
- [ ] Database queries fast
- [ ] Batch processor completing

### User Experience
- [ ] Thoughts can be created
- [ ] Analysis is meaningful
- [ ] Results are accurate
- [ ] Performance is acceptable
- [ ] Weekly synthesis works

### Business Metrics
- [ ] Cost per thought acceptable
- [ ] Processing time acceptable
- [ ] Cache hit rate good (>20%)
- [ ] Error rate low (<1%)
- [ ] User satisfaction high

## 🎉 Launch Checklist

### Pre-Launch
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Monitoring configured
- [ ] Backups working
- [ ] Security reviewed

### Launch Day
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Test end-to-end flow
- [ ] Monitor for errors
- [ ] Announce availability

### Post-Launch
- [ ] Monitor logs closely (first 24h)
- [ ] Check costs daily (first week)
- [ ] Gather user feedback
- [ ] Document issues
- [ ] Plan improvements

## 📞 Emergency Contacts

Add your team's contact information:

- **On-call Engineer**: _________________
- **DevOps Lead**: _________________
- **Product Owner**: _________________
- **Anthropic Support**: support@anthropic.com
- **OpenAI Support**: help.openai.com
- **Supabase Support**: support.supabase.com

## 🆘 Rollback Plan

If deployment fails:

1. **Immediate Actions**:
   - [ ] Stop accepting new requests
   - [ ] Identify the issue
   - [ ] Check logs for errors

2. **Rollback Steps**:
   - [ ] Revert to previous Docker images
   - [ ] Restore database from backup (if needed)
   - [ ] Verify system health
   - [ ] Resume normal operations

3. **Post-Mortem**:
   - [ ] Document what went wrong
   - [ ] Identify root cause
   - [ ] Plan prevention measures
   - [ ] Update deployment process

---

## Summary

Before going live, ensure:
- ✅ All API keys valid and tested
- ✅ Database initialized and accessible
- ✅ Deployment method chosen and configured
- ✅ Security measures in place
- ✅ Monitoring and alerting setup
- ✅ Backup strategy implemented
- ✅ Documentation complete
- ✅ Emergency contacts documented
- ✅ Rollback plan ready

**Status**: Ready for Production? _____ (Yes/No)

**Deployed By**: _________________
**Deployment Date**: _________________
**Environment**: _________________

---

**Good luck with your deployment! 🚀**

For help, see [README.md](README.md) or [SETUP.md](SETUP.md)
