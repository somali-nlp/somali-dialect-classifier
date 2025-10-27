# Production Deployment Guide

Comprehensive guide to deploying the Somali Dialect Classifier preprocessing pipeline in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Environment Configuration](#environment-configuration)
4. [Scheduling and Orchestration](#scheduling-and-orchestration)
5. [Docker Deployment](#docker-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
9. [Scaling Considerations](#scaling-considerations)
10. [Security Hardening](#security-hardening)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum Requirements**:
- **Python**: 3.9 or higher
- **CPU**: 2 cores
- **RAM**: 4GB (8GB recommended for Wikipedia processing)
- **Disk**: 50GB for data storage
- **Network**: Stable internet connection for scraping

**Recommended Production**:
- **Python**: 3.11
- **CPU**: 4-8 cores
- **RAM**: 16GB
- **Disk**: 500GB SSD (scalable to TB+ for long-term storage)
- **Network**: 100Mbps+ bandwidth

### Operating System

Tested on:
- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+
- **macOS**: 12.0+ (Monterey)
- **Windows**: Windows 10+ (via WSL2 recommended)

### Dependencies

**Core Dependencies**:
```bash
# Python packages
requests>=2.31
tqdm>=4.65
pyarrow>=14
beautifulsoup4>=4.12
lxml>=4.9

# Optional (config management)
pydantic>=2.5
pydantic-settings>=2.1
python-dotenv>=1.0
```

**System Libraries** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3-pip \
  build-essential \
  libbz2-dev \
  liblzma-dev \
  libxml2-dev \
  libxslt1-dev
```

---

## Installation

### Option 1: pip Install (Production)

```bash
# Create virtual environment
python3.11 -m venv /opt/somali-nlp/venv
source /opt/somali-nlp/venv/bin/activate

# Install from PyPI (when published)
pip install somali-dialect-classifier[config]

# Or install from Git repository
pip install git+https://github.com/your-org/somali-dialect-classifier.git

# Verify installation
wikisom-download --help
bbcsom-download --help
```

### Option 2: Editable Install (Development)

```bash
# Clone repository
git clone https://github.com/your-org/somali-dialect-classifier.git
cd somali-dialect-classifier

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install in editable mode
pip install -e ".[dev,config]"

# Run tests
pytest
```

### Post-Installation Setup

```bash
# Create data directories
mkdir -p /data/raw /data/staging /data/processed/silver /logs

# Set permissions
chmod 755 /data /logs
chmod 644 /data/raw/*  # Read-only raw data

# Verify paths
ls -la /data/
```

---

## Environment Configuration

### Production Configuration File

Create `/etc/somali-nlp/config.env`:

```bash
# Data paths (absolute paths in production)
SDC_DATA__RAW_DIR=/data/raw
SDC_DATA__SILVER_DIR=/data/processed/silver
SDC_DATA__STAGING_DIR=/data/staging
SDC_DATA__PROCESSED_DIR=/data/processed

# Logging
SDC_LOGGING__LEVEL=INFO
SDC_LOGGING__LOG_DIR=/var/log/somali-nlp

# BBC scraping (ethical defaults)
SDC_SCRAPING__BBC__MIN_DELAY=2.0
SDC_SCRAPING__BBC__MAX_DELAY=5.0
SDC_SCRAPING__BBC__TIMEOUT=30
SDC_SCRAPING__BBC__USER_AGENT="SomaliNLP/1.0 (Research; +https://yoursite.com)"

# Wikipedia scraping
SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=100
SDC_SCRAPING__WIKIPEDIA__TIMEOUT=30
```

### Load Configuration

```bash
# Export environment variables
export $(cat /etc/somali-nlp/config.env | xargs)

# Or use systemd EnvironmentFile (recommended)
```

### Systemd Service

Create `/etc/systemd/system/somali-nlp-bbc.service`:

```ini
[Unit]
Description=Somali NLP BBC Scraper
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=somali-nlp
Group=somali-nlp
WorkingDirectory=/opt/somali-nlp

# Load environment
EnvironmentFile=/etc/somali-nlp/config.env

# Activate virtual environment and run
ExecStart=/opt/somali-nlp/venv/bin/bbcsom-download --max-articles 1000

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=somali-nlp-bbc

# Resource limits
MemoryMax=8G
CPUQuota=400%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data /var/log/somali-nlp

[Install]
WantedBy=multi-user.target
```

**Enable and run**:
```bash
# Enable service
sudo systemctl daemon-reload
sudo systemctl enable somali-nlp-bbc.service

# Run manually
sudo systemctl start somali-nlp-bbc.service

# Check status
sudo systemctl status somali-nlp-bbc.service

# View logs
sudo journalctl -u somali-nlp-bbc.service -f
```

---

## Scheduling and Orchestration

### Cron Scheduling

For simple periodic execution:

**Edit crontab**:
```bash
sudo crontab -e -u somali-nlp
```

**Add schedule**:
```cron
# Run BBC scraper daily at 2 AM
0 2 * * * /opt/somali-nlp/venv/bin/bbcsom-download --max-articles 1000 >> /var/log/somali-nlp/bbc-cron.log 2>&1

# Run Wikipedia processor weekly on Sunday at 3 AM
0 3 * * 0 /opt/somali-nlp/venv/bin/wikisom-download >> /var/log/somali-nlp/wiki-cron.log 2>&1

# Cleanup old logs monthly
0 4 1 * * find /var/log/somali-nlp -name "*.log" -mtime +30 -delete
```

**Cron with environment**:
```bash
#!/bin/bash
# /opt/somali-nlp/scripts/run-bbc-scraper.sh

source /etc/somali-nlp/config.env
source /opt/somali-nlp/venv/bin/activate
bbcsom-download --max-articles 1000
```

### Systemd Timers (Recommended)

More reliable than cron with better logging and dependencies.

**Create timer**: `/etc/systemd/system/somali-nlp-bbc.timer`:

```ini
[Unit]
Description=Somali NLP BBC Scraper Daily Timer
Requires=somali-nlp-bbc.service

[Timer]
# Run daily at 2 AM
OnCalendar=daily
OnCalendar=*-*-* 02:00:00

# Run 10 minutes after boot if missed
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
```

**Enable timer**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable somali-nlp-bbc.timer
sudo systemctl start somali-nlp-bbc.timer

# Check timer status
sudo systemctl list-timers
```

### Prefect Orchestration

For complex workflows with retries, dependencies, and monitoring.

**Install Prefect**:
```bash
pip install "somali-dialect-classifier[mlops]"
```

**New Orchestration Features (v3.0+)**:

The orchestrator now supports several production-ready features:

1. **Source Skipping**: Skip specific data sources when running all pipelines
   ```bash
   somali-orchestrate --pipeline all --skip-sources bbc huggingface
   ```

2. **Språkbanken Corpus Selection**: Choose specific corpus instead of all 23
   ```bash
   somali-orchestrate --pipeline all --sprakbanken-corpus cilmi
   ```

3. **Auto-Deploy Dashboard**: Automatically deploy metrics after successful runs
   ```bash
   somali-orchestrate --pipeline all --auto-deploy
   ```

4. **Testing Limits**: Limit records for quick testing
   ```bash
   somali-orchestrate --pipeline all --max-bbc-articles 100 --max-hf-records 1000
   ```

5. **Proper Exit Codes**: Returns exit code 1 on failures (critical for CI/CD)
   ```bash
   somali-orchestrate --pipeline all || echo "Pipeline failed with code $?"
   ```

**Create flow**: `flows/bbc_scraper_flow.py`:

```python
from prefect import flow, task
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor
import logging

@task(retries=3, retry_delay_seconds=300)
def scrape_bbc_articles(max_articles: int):
    """Scrape BBC Somali articles with retries."""
    processor = BBCSomaliProcessor(max_articles=max_articles)
    return processor.run()

@task
def validate_output(output_path):
    """Validate output file exists and has content."""
    assert output_path.exists(), f"Output not found: {output_path}"
    # Additional validation...
    logging.info(f"Validation passed: {output_path}")

@flow(name="bbc-somali-scraper")
def bbc_scraper_flow(max_articles: int = 1000):
    """Daily BBC Somali scraping flow."""
    output_path = scrape_bbc_articles(max_articles)
    validate_output(output_path)
    return output_path

if __name__ == "__main__":
    bbc_scraper_flow()
```

**Schedule with Prefect**:
```bash
# Start Prefect server (or use Prefect Cloud)
prefect server start

# Deploy flow
prefect deployment build flows/bbc_scraper_flow.py:bbc_scraper_flow \
  --name daily-bbc-scraper \
  --cron "0 2 * * *" \
  --apply

# Start agent to run scheduled flows
prefect agent start -q default
```

### Airflow DAG

For enterprise-grade orchestration with monitoring and alerting.

**Create DAG**: `dags/somali_nlp_dag.py`:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor, WikipediaSomaliProcessor

default_args = {
    'owner': 'somali-nlp',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email': ['alerts@yourorg.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'somali_nlp_pipeline',
    default_args=default_args,
    description='Somali NLP data pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    max_active_runs=1,
)

def scrape_bbc(**context):
    processor = BBCSomaliProcessor(max_articles=1000)
    output_path = processor.run()
    return str(output_path)

def process_wikipedia(**context):
    processor = WikipediaSomaliProcessor()
    output_path = processor.run()
    return str(output_path)

task_bbc = PythonOperator(
    task_id='scrape_bbc',
    python_callable=scrape_bbc,
    dag=dag,
)

task_wiki = PythonOperator(
    task_id='process_wikipedia',
    python_callable=process_wikipedia,
    dag=dag,
)

# Tasks can run in parallel
task_bbc
task_wiki
```

---

## Docker Deployment

### Dockerfile

**Create `Dockerfile`**:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libbz2-dev \
    liblzma-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 somali-nlp

# Set working directory
WORKDIR /app

# Copy requirements
COPY pyproject.toml README.md ./
COPY src/ src/

# Install package
RUN pip install --no-cache-dir -e ".[config]"

# Create data directories
RUN mkdir -p /data/raw /data/staging /data/processed/silver /logs && \
    chown -R somali-nlp:somali-nlp /data /logs

# Switch to non-root user
USER somali-nlp

# Set environment defaults (can be overridden)
ENV SDC_DATA__RAW_DIR=/data/raw
ENV SDC_DATA__SILVER_DIR=/data/processed/silver
ENV SDC_LOGGING__LOG_DIR=/logs
ENV SDC_LOGGING__LEVEL=INFO

# Default command
CMD ["bbcsom-download", "--max-articles", "1000"]
```

### Docker Compose

**Create `docker-compose.yml`**:

```yaml
version: '3.8'

services:
  bbc-scraper:
    build: .
    image: somali-nlp:latest
    container_name: somali-nlp-bbc
    environment:
      - SDC_DATA__RAW_DIR=/data/raw
      - SDC_DATA__SILVER_DIR=/data/processed/silver
      - SDC_LOGGING__LEVEL=INFO
      - SDC_SCRAPING__BBC__MAX_ARTICLES=1000
      - SDC_SCRAPING__BBC__MIN_DELAY=2.0
      - SDC_SCRAPING__BBC__MAX_DELAY=5.0
    volumes:
      - ./data:/data
      - ./logs:/logs
    command: ["bbcsom-download"]
    restart: on-failure
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  wikipedia-processor:
    build: .
    image: somali-nlp:latest
    container_name: somali-nlp-wiki
    environment:
      - SDC_DATA__RAW_DIR=/data/raw
      - SDC_DATA__SILVER_DIR=/data/processed/silver
      - SDC_LOGGING__LEVEL=INFO
    volumes:
      - ./data:/data
      - ./logs:/logs
    command: ["wikisom-download"]
    restart: on-failure
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
```

### Build and Run

```bash
# Build image
docker-compose build

# Run BBC scraper
docker-compose up bbc-scraper

# Run Wikipedia processor
docker-compose up wikipedia-processor

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f bbc-scraper

# Stop containers
docker-compose down
```

### Docker in Production

```bash
# Use specific version tags
docker pull somali-nlp:1.0.0

# Run with restart policy
docker run -d \
  --name somali-nlp-bbc \
  --restart unless-stopped \
  -v /data:/data \
  -v /logs:/logs \
  -e SDC_LOGGING__LEVEL=INFO \
  somali-nlp:1.0.0 \
  bbcsom-download --max-articles 1000

# Schedule with systemd timer
```

---

## Cloud Deployment

### AWS Deployment

#### EC2 Instance Setup

```bash
# Launch EC2 instance (t3.large recommended)
# Amazon Linux 2023 or Ubuntu 22.04

# Install dependencies
sudo yum install -y python3.11 python3.11-pip git

# Clone and install
git clone https://github.com/your-org/somali-dialect-classifier.git
cd somali-dialect-classifier
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[config]"

# Configure with AWS Systems Manager Parameter Store
aws ssm get-parameter --name /somali-nlp/config --query Parameter.Value --output text > /etc/somali-nlp/config.env
```

#### S3 Storage

```bash
# Install AWS CLI
pip install awscli

# Mount S3 bucket using s3fs
pip install s3fs

# Configure environment
export SDC_DATA__RAW_DIR=s3://somali-nlp-data/raw
export SDC_DATA__SILVER_DIR=s3://somali-nlp-data/silver
```

**Python code for S3**:
```python
import s3fs
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# S3 filesystem
fs = s3fs.S3FileSystem()

# Run pipeline (writes directly to S3)
processor = BBCSomaliProcessor(max_articles=1000)
processor.run()
```

#### ECS/Fargate Deployment

**Task definition** (`task-definition.json`):

```json
{
  "family": "somali-nlp-bbc",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/somali-nlp-task-role",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "bbc-scraper",
      "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/somali-nlp:latest",
      "cpu": 2048,
      "memory": 8192,
      "essential": true,
      "environment": [
        {"name": "SDC_DATA__RAW_DIR", "value": "/mnt/efs/raw"},
        {"name": "SDC_DATA__SILVER_DIR", "value": "/mnt/efs/silver"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "efs-data",
          "containerPath": "/mnt/efs"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/somali-nlp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "bbc"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "efs-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-12345678",
        "transitEncryption": "ENABLED"
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192"
}
```

**Deploy**:
```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Run task
aws ecs run-task \
  --cluster somali-nlp-cluster \
  --task-definition somali-nlp-bbc \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### EventBridge Scheduling

```bash
# Create EventBridge rule for daily execution
aws events put-rule \
  --name somali-nlp-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

# Add ECS task as target
aws events put-targets \
  --rule somali-nlp-daily \
  --targets "Id=1,Arn=arn:aws:ecs:REGION:ACCOUNT:cluster/somali-nlp-cluster,RoleArn=arn:aws:iam::ACCOUNT:role/ecsEventsRole,EcsParameters={TaskDefinitionArn=arn:aws:ecs:REGION:ACCOUNT:task-definition/somali-nlp-bbc:1,LaunchType=FARGATE}"
```

### GCP Deployment

#### Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/somali-nlp

# Deploy to Cloud Run
gcloud run deploy somali-nlp-bbc \
  --image gcr.io/PROJECT_ID/somali-nlp \
  --platform managed \
  --region us-central1 \
  --memory 8Gi \
  --cpu 4 \
  --timeout 3600 \
  --set-env-vars SDC_LOGGING__LEVEL=INFO \
  --set-env-vars SDC_DATA__RAW_DIR=/mnt/gcs/raw \
  --set-env-vars SDC_DATA__SILVER_DIR=/mnt/gcs/silver
```

#### Cloud Scheduler

```bash
# Create scheduler job
gcloud scheduler jobs create http somali-nlp-daily \
  --schedule "0 2 * * *" \
  --uri "https://somali-nlp-bbc-XXX.a.run.app" \
  --http-method POST \
  --oidc-service-account-email somali-nlp@PROJECT_ID.iam.gserviceaccount.com
```

### Azure Deployment

#### Container Instances

```bash
# Create container instance
az container create \
  --resource-group somali-nlp-rg \
  --name somali-nlp-bbc \
  --image somalinlp.azurecr.io/somali-nlp:latest \
  --cpu 4 \
  --memory 8 \
  --environment-variables \
    SDC_LOGGING__LEVEL=INFO \
    SDC_DATA__RAW_DIR=/mnt/azure/raw \
  --azure-file-volume-account-name somalinlpdata \
  --azure-file-volume-account-key $STORAGE_KEY \
  --azure-file-volume-share-name data \
  --azure-file-volume-mount-path /mnt/azure
```

---

## Monitoring and Alerting

### Logging

**Structured logging**:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        return json.dumps(log_data)

handler = logging.FileHandler("/var/log/somali-nlp/pipeline.log")
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("somali_dialect_classifier")
logger.addHandler(handler)
```

### Metrics Collection

**Prometheus metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
articles_processed = Counter('articles_processed_total', 'Total articles processed')
processing_time = Histogram('processing_duration_seconds', 'Time to process articles')
active_pipelines = Gauge('active_pipelines', 'Number of active pipelines')

# Instrument code
with processing_time.time():
    processor.run()
    articles_processed.inc()

# Start metrics server
start_http_server(8000)
```

### Health Checks

**Create health endpoint**:
```python
from flask import Flask, jsonify
from pathlib import Path

app = Flask(__name__)

@app.route('/health')
def health():
    # Check data directories accessible
    data_ok = Path('/data/raw').exists() and Path('/data/silver').exists()

    # Check recent processing
    recent_file = max(Path('/data/silver').rglob('*.parquet'), default=None)
    processing_ok = recent_file and (datetime.now() - datetime.fromtimestamp(recent_file.stat().st_mtime)).days < 1

    status = 'healthy' if (data_ok and processing_ok) else 'unhealthy'

    return jsonify({
        'status': status,
        'data_accessible': data_ok,
        'recent_processing': processing_ok
    }), 200 if status == 'healthy' else 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Alerting

**PagerDuty integration**:
```python
import requests

def send_alert(message):
    payload = {
        "routing_key": "YOUR_INTEGRATION_KEY",
        "event_action": "trigger",
        "payload": {
            "summary": message,
            "severity": "error",
            "source": "somali-nlp-pipeline"
        }
    }
    requests.post("https://events.pagerduty.com/v2/enqueue", json=payload)

# In pipeline
try:
    processor.run()
except Exception as e:
    send_alert(f"Pipeline failed: {e}")
    raise
```

---

## Backup and Disaster Recovery

### Backup Strategy

**3-2-1 Rule**:
- 3 copies of data
- 2 different media types
- 1 off-site backup

**Backup script**:
```bash
#!/bin/bash
# /opt/somali-nlp/scripts/backup.sh

BACKUP_DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/somali-nlp/$BACKUP_DATE

# Create backup
mkdir -p $BACKUP_DIR
rsync -av --progress /data/processed/silver/ $BACKUP_DIR/silver/

# Compress
tar -czf $BACKUP_DIR/silver.tar.gz -C $BACKUP_DIR silver/

# Upload to S3
aws s3 cp $BACKUP_DIR/silver.tar.gz s3://somali-nlp-backups/silver/$BACKUP_DATE/

# Cleanup old local backups (keep 7 days)
find /backup/somali-nlp/ -type d -mtime +7 -exec rm -rf {} +
```

**Schedule backup**:
```cron
# Daily backup at 4 AM
0 4 * * * /opt/somali-nlp/scripts/backup.sh >> /var/log/somali-nlp/backup.log 2>&1
```

### Disaster Recovery

**Recovery plan**:

1. **Restore from backup**:
```bash
# Download latest backup
aws s3 cp s3://somali-nlp-backups/silver/latest.tar.gz /tmp/

# Extract
tar -xzf /tmp/latest.tar.gz -C /data/processed/

# Verify integrity
python -c "import pyarrow.parquet as pq; pq.read_table('/data/processed/silver/source=BBC-Somali/date_accessed=2025-01-15').validate()"
```

2. **Re-run pipeline** (if backup unavailable):
```bash
# Re-scrape BBC (within rate limits)
bbcsom-download --max-articles 1000 --force

# Re-download Wikipedia dump
wikisom-download --force
```

### Data Retention Policy

```python
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_data(base_dir: Path, retention_days: int):
    """Remove data older than retention_days."""
    cutoff = datetime.now() - timedelta(days=retention_days)

    for partition in base_dir.rglob('date_accessed=*'):
        date_str = partition.name.split('=')[1]
        date = datetime.strptime(date_str, '%Y-%m-%d')

        if date < cutoff:
            print(f"Removing old partition: {partition}")
            shutil.rmtree(partition)

# Cleanup old raw data (keep 30 days)
cleanup_old_data(Path('/data/raw'), retention_days=30)

# Keep silver data longer (365 days)
cleanup_old_data(Path('/data/processed/silver'), retention_days=365)
```

---

## Scaling Considerations

### Horizontal Scaling

**Distributed scraping** (BBC):
```python
# Split article list across workers
from multiprocessing import Pool

def scrape_article_batch(article_links):
    processor = BBCSomaliProcessor()
    # Process batch...

# Distribute work
with Pool(processes=4) as pool:
    results = pool.map(scrape_article_batch, article_batches)
```

**Kubernetes deployment**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: somali-nlp-bbc
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      parallelism: 4
      completions: 1
      template:
        spec:
          containers:
          - name: bbc-scraper
            image: somali-nlp:latest
            resources:
              requests:
                memory: "8Gi"
                cpu: "4"
              limits:
                memory: "16Gi"
                cpu: "8"
          restartPolicy: OnFailure
```

### Vertical Scaling

**Optimize memory usage**:
```python
# Stream processing for large files
def process_wikipedia_streaming():
    processor = WikipediaSomaliProcessor(batch_size=1000)
    # Writes in batches, prevents OOM
    processor.run()
```

**Increase resources**:
```bash
# systemd service limits
MemoryMax=32G
CPUQuota=800%

# Docker limits
docker run -m 32g --cpus 8 somali-nlp:latest
```

---

## Security Hardening

### Network Security

```bash
# Firewall rules (allow only necessary traffic)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Restrict outbound connections
# Only allow BBC, Wikipedia, etc.
```

### File Permissions

```bash
# Restrict access to data directories
chown -R somali-nlp:somali-nlp /data /logs
chmod 750 /data /logs
chmod 640 /data/raw/*/*

# Protect config files
chmod 600 /etc/somali-nlp/config.env
chown root:root /etc/somali-nlp/config.env
```

### Secret Management

**Use AWS Secrets Manager**:
```python
import boto3

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='somali-nlp/api-keys')
secrets = json.loads(response['SecretString'])

os.environ['SDC_SCRAPING__API_KEY'] = secrets['api_key']
```

### Audit Logging

```python
import logging

audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('/var/log/somali-nlp/audit.log')
audit_logger.addHandler(audit_handler)

def audit_log(action, user, details):
    audit_logger.info(f"ACTION={action} USER={user} DETAILS={details}")

# Log all scraping activities
audit_log('SCRAPE_START', 'systemd', 'source=BBC articles=1000')
```

---

## Troubleshooting

### Common Issues

#### 1. Memory Issues

**Symptom**: OOMKilled, process crashes

**Solution**:
```bash
# Check memory usage
free -h
docker stats

# Reduce batch size
export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50

# Increase memory limits
# Edit systemd service: MemoryMax=16G
```

#### 2. Rate Limiting

**Symptom**: 429 errors, scraper blocked

**Solution**:
```bash
# Increase delays
export SDC_SCRAPING__BBC__MIN_DELAY=5.0
export SDC_SCRAPING__BBC__MAX_DELAY=10.0

# Check robots.txt compliance
curl https://www.bbc.com/robots.txt
```

#### 3. Disk Space

**Symptom**: No space left on device

**Solution**:
```bash
# Check disk usage
df -h
du -sh /data/*

# Cleanup old data
find /data/raw -type f -mtime +30 -delete

# Enable log rotation
sudo nano /etc/logrotate.d/somali-nlp
```

#### 4. Configuration Not Loading

**Symptom**: Using wrong paths or defaults

**Solution**:
```bash
# Verify environment
env | grep SDC_

# Check config loading
python -c "from somali_dialect_classifier.config import get_config; print(get_config().data.raw_dir)"

# Reload systemd config
sudo systemctl daemon-reload
sudo systemctl restart somali-nlp-bbc.service
```

### Debug Mode

```bash
# Enable debug logging
export SDC_LOGGING__LEVEL=DEBUG

# Run with verbose output
bbcsom-download --max-articles 10 2>&1 | tee debug.log

# Check logs
tail -f /var/log/somali-nlp/pipeline.log | grep ERROR
```

---

## See Also

- [Configuration Guide](CONFIGURATION.md) - Environment variables and settings
- [API Reference](API_REFERENCE.md) - Programmatic APIs
- [Architecture Documentation](ARCHITECTURE.md) - System design
- [Data Pipeline](DATA_PIPELINE.md) - ETL pipeline details
- [Testing Guide](TESTING.md) - Testing strategies

---

**Last Updated**: 2025-10-27
**Maintainers**: Somali NLP Contributors
