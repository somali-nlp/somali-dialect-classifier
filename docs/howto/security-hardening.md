# Security Hardening Guide

**Comprehensive guide to security features and best practices in the Somali Dialect Classifier project.**

**Last Updated:** 2026-01-06

---

## Table of Contents

1. [Overview](#overview)
2. [XXE Protection](#xxe-protection)
3. [SQL Injection Prevention](#sql-injection-prevention)
4. [Password Validation](#password-validation)
5. [Log Redaction](#log-redaction)
6. [Network Security](#network-security)
7. [Dependency Security](#dependency-security)
8. [Security Checklist](#security-checklist)

---

## Overview

The project includes comprehensive security hardening to protect against common vulnerabilities. This guide explains each security feature and provides best practices for production deployments.

**Security Principles**:
- Defense in depth (multiple layers of protection)
- Fail-safe defaults (secure by default)
- Least privilege (minimal permissions)
- Security by design (not an afterthought)

---

## XXE Protection

### What is XXE?

**XML External Entity (XXE)** attacks exploit XML parsers that process external entity references, potentially leading to:
- File disclosure (read sensitive files)
- Server-Side Request Forgery (SSRF)
- Denial of Service (DoS)

### How We Prevent XXE

The project uses **defusedxml** instead of Python's standard library XML parsers:

```python
# INSECURE (vulnerable to XXE)
import xml.etree.ElementTree as ET
tree = ET.parse(xml_file)  # ❌ DON'T USE

# SECURE (XXE protection)
from defusedxml.ElementTree import parse
tree = parse(xml_file)  # ✅ USE THIS
```

### Affected Processors

XXE protection is critical for processors that parse XML:

1. **Wikipedia Processor** (`wikipedia_somali_processor.py`)
   - Parses MediaWiki XML dumps
   - Uses `defusedxml.ElementTree.iterparse()`

2. **Språkbanken Processor** (`sprakbanken_somali_processor.py`)
   - Parses corpus XML files
   - Uses `defusedxml.ElementTree.parse()`

### Verification

Check that defusedxml is installed:

```bash
pip list | grep defusedxml
# Should show: defusedxml  0.7.1+
```

### Best Practices

- **Always use defusedxml** for XML parsing
- **Never disable XXE protection** in production
- **Update regularly**: `pip install --upgrade defusedxml`
- **Audit XML sources**: Only parse XML from trusted sources

### Further Reading

- [OWASP XXE Prevention](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html)
- [defusedxml Documentation](https://pypi.org/project/defusedxml/)

---

## SQL Injection Prevention

### How We Prevent SQL Injection

The project uses **parameterized queries** for all database operations:

```python
# INSECURE (SQL injection vulnerability)
query = f"SELECT * FROM crawl_ledger WHERE url = '{url}'"  # ❌ DON'T USE
cursor.execute(query)

# SECURE (parameterized query)
query = "SELECT * FROM crawl_ledger WHERE url = %s"  # ✅ USE THIS
cursor.execute(query, (url,))
```

### Affected Components

1. **Crawl Ledger** (`crawl_ledger.py`)
   - All URL lookups use parameterized queries
   - State updates use parameterized queries

2. **PostgreSQL Backend** (`postgres_backend.py`)
   - All queries use SQLAlchemy ORM or parameterized SQL
   - LIMIT clause validation prevents injection

### LIMIT Clause Validation

Special handling for LIMIT clauses:

```python
# Validate LIMIT value
def validate_limit(limit: int) -> int:
    """Ensure LIMIT is a valid integer."""
    if not isinstance(limit, int) or limit < 0:
        raise ValueError(f"Invalid LIMIT value: {limit}")
    return limit

# Use in query
query = f"SELECT * FROM crawl_ledger LIMIT {validate_limit(limit)}"
```

### Safe Query Construction

When dynamic query construction is needed:

```python
# Use SQLAlchemy for complex queries
from sqlalchemy import select, and_

stmt = select(CrawlLedger).where(
    and_(
        CrawlLedger.source == source,
        CrawlLedger.state == state
    )
).limit(limit)
```

### Best Practices

- **Use ORMs** (SQLAlchemy) whenever possible
- **Parameterize all user input** in queries
- **Validate input types** before query construction
- **Audit raw SQL** in code reviews

### Further Reading

- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

---

## Password Validation

### Requirements

**PostgreSQL password validation is enforced**:

- **Minimum length**: 8 characters (16+ recommended for production)
- **Must be set**: Via `SDC_DB_PASSWORD` or `POSTGRES_PASSWORD`
- **Never hardcoded**: Must come from environment variables
- **Never committed**: `.env` files excluded from git

### Setting Passwords

**Development**:

```bash
# Create .env file
echo "SDC_DB_PASSWORD=dev_password_123" > .env
```

**Production**:

```bash
# Generate strong password
export SDC_DB_PASSWORD="$(openssl rand -base64 32)"

# Or use secret manager (AWS Secrets Manager, HashiCorp Vault)
export SDC_DB_PASSWORD="$(aws secretsmanager get-secret-value --secret-id somali-db-password --query SecretString --output text)"
```

### Password Storage Best Practices

**Never do this**:

```python
# ❌ INSECURE - Hardcoded password
password = "my_password_123"

# ❌ INSECURE - Password in code
POSTGRES_PASSWORD = "secret123"
```

**Always do this**:

```python
# ✅ SECURE - Environment variable
import os
password = os.environ.get("SDC_DB_PASSWORD")

# ✅ SECURE - Pydantic Settings (validates presence)
from somali_dialect_classifier.config import get_config
password = get_config().db.password
```

### Password Rotation

Rotate passwords regularly (quarterly recommended):

```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update PostgreSQL
psql -h localhost -U somali -d somali_nlp -c \
  "ALTER USER somali WITH PASSWORD '$NEW_PASSWORD';"

# Update environment
export SDC_DB_PASSWORD="$NEW_PASSWORD"

# Update .env (for Docker)
sed -i "s/SDC_DB_PASSWORD=.*/SDC_DB_PASSWORD=$NEW_PASSWORD/" .env
docker-compose restart postgres
```

### Secret Management

**Production Secret Managers**:

1. **AWS Secrets Manager**:
   ```bash
   aws secretsmanager create-secret \
     --name somali-db-password \
     --secret-string "$(openssl rand -base64 32)"
   ```

2. **HashiCorp Vault**:
   ```bash
   vault kv put secret/somali-db password="$(openssl rand -base64 32)"
   ```

3. **Kubernetes Secrets**:
   ```bash
   kubectl create secret generic somali-db-password \
     --from-literal=password="$(openssl rand -base64 32)"
   ```

### Best Practices

- **Minimum 16 characters** for production
- **Use secret managers** for production deployments
- **Rotate quarterly** or after incidents
- **Audit access** to secrets
- **Never log passwords** (see Log Redaction)

### Further Reading

- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [PostgreSQL Setup - Security](../operations/postgres-setup.md#security)

---

## Log Redaction

### What Gets Redacted

Sensitive data is automatically redacted from logs:

- **Passwords**: Database passwords, API keys
- **Tokens**: Authentication tokens, API tokens
- **Credentials**: Any field matching `password`, `token`, `secret`, `key`

### Implementation

```python
# In logging_utils.py
def redact_sensitive_data(message: str) -> str:
    """Redact sensitive information from log messages."""
    patterns = [
        (r'password["\s:=]+\S+', 'password=<REDACTED>'),
        (r'token["\s:=]+\S+', 'token=<REDACTED>'),
        (r'api_key["\s:=]+\S+', 'api_key=<REDACTED>'),
    ]
    for pattern, replacement in patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message
```

### Example

**Before redaction**:
```
INFO: Connecting to database with password=mySecretPassword123
```

**After redaction**:
```
INFO: Connecting to database with password=<REDACTED>
```

### Audit Trail Considerations

- **Redaction preserves structure**: `password=<REDACTED>` shows field exists
- **Audit logs unchanged**: Database audit logs unaffected
- **Separate sensitive logs**: Use separate log files for sensitive operations

### Best Practices

- **Log structured data** (JSON) for easier redaction
- **Use log levels** (DEBUG, INFO, WARNING, ERROR)
- **Avoid logging credentials** even before redaction
- **Review logs regularly** for unredacted sensitive data

### Further Reading

- [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

---

## Network Security

### SSRF Protection

**Server-Side Request Forgery (SSRF)** attacks trick servers into making unintended requests.

**URL Validation**:

```python
# Validate URLs before fetching
def validate_url(url: str) -> bool:
    """Ensure URL is safe to fetch."""
    parsed = urlparse(url)

    # Block private IPs
    if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
        return False

    # Block private networks
    if parsed.hostname.startswith('192.168.') or parsed.hostname.startswith('10.'):
        return False

    # Require HTTPS for production
    if parsed.scheme != 'https':
        logger.warning(f"Non-HTTPS URL: {url}")

    return True
```

### Timeout Configuration

Prevent resource exhaustion with timeouts:

```bash
# HTTP request timeout (default: 30s)
SDC_HTTP__REQUEST_TIMEOUT=30

# Database query timeout (default: 30s)
SDC_DB__QUERY_TIMEOUT=30
```

### Rate Limiting

Ethical web scraping with rate limiting:

```python
# BBC scraping (default: 1-3s delay)
SDC_SCRAPING__BBC__MIN_DELAY=1.0
SDC_SCRAPING__BBC__MAX_DELAY=3.0

# Respect robots.txt
from urllib.robotparser import RobotFileParser
rp = RobotFileParser()
rp.set_url("https://www.bbc.com/robots.txt")
rp.read()
can_fetch = rp.can_fetch("SomaliNLP-Bot", url)
```

### Best Practices

- **Validate all URLs** before fetching
- **Block private IPs** (localhost, 192.168.*, 10.*)
- **Use HTTPS** for all external requests
- **Set timeouts** on all network operations
- **Rate limit** all external requests
- **Respect robots.txt** for web scraping

### Further Reading

- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

---

## Dependency Security

### Automated Scanning

Use `pip-audit` to scan for vulnerabilities:

```bash
# Install pip-audit
pip install pip-audit

# Scan dependencies
pip-audit

# Scan with auto-fix (updates vulnerable packages)
pip-audit --fix
```

### Keeping Dependencies Updated

**Regular updates** (monthly recommended):

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade defusedxml

# Update all dependencies (test first!)
pip install --upgrade -r requirements.txt
```

### Security Patch Monitoring

**GitHub Dependabot** (automated):

1. Enable Dependabot in repository settings
2. Receives automatic PRs for security updates
3. Review and merge security patches

**Manual monitoring**:

```bash
# Subscribe to security advisories
# - PyPI security advisories: https://pypi.org/security/
# - GitHub Security Lab: https://securitylab.github.com/
```

### Dependency Pinning

Balance security and stability:

```toml
# pyproject.toml - Pin major versions, allow minor updates
dependencies = [
    "defusedxml>=0.7.1,<1.0",  # Allow 0.7.x updates
    "psycopg2-binary>=2.9,<3.0",
    "pydantic>=2.0,<3.0",
]
```

### Best Practices

- **Run pip-audit monthly** or in CI/CD
- **Update dependencies regularly** (monthly)
- **Pin major versions** to prevent breaking changes
- **Test updates** before production deployment
- **Monitor security advisories** for critical dependencies
- **Use virtual environments** to isolate dependencies

### Further Reading

- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)
- [pip-audit Documentation](https://pypi.org/project/pip-audit/)

---

## Security Checklist

### Pre-Production Checklist

Use this checklist before deploying to production:

#### Configuration

- [ ] Strong PostgreSQL password set (16+ characters)
- [ ] Password stored in secret manager (not .env)
- [ ] `.env` file excluded from git (.gitignore)
- [ ] All sensitive config in environment variables
- [ ] Timeouts configured (HTTP, DB)
- [ ] Connection pool sized appropriately

#### Dependencies

- [ ] `defusedxml` installed and up-to-date
- [ ] `pip-audit` scan passed (no high/critical vulnerabilities)
- [ ] All dependencies pinned to major versions
- [ ] Dependabot enabled for automated security updates

#### Network

- [ ] HTTPS enforced for all external requests
- [ ] URL validation implemented for user input
- [ ] Rate limiting configured for web scraping
- [ ] `robots.txt` respected

#### Database

- [ ] Parameterized queries used (no string interpolation)
- [ ] LIMIT clause validation implemented
- [ ] Connection pool properly configured
- [ ] Query timeouts configured

#### Logging

- [ ] Sensitive data redaction enabled
- [ ] Log levels appropriate (INFO for production)
- [ ] Logs written to secure location
- [ ] Log rotation configured

#### Access Control

- [ ] Least privilege database user
- [ ] PostgreSQL port not exposed publicly (localhost only)
- [ ] Docker networks configured properly
- [ ] No default passwords in use

### Incident Response

If a security incident occurs:

1. **Isolate**: Disconnect affected systems
2. **Assess**: Determine scope and impact
3. **Contain**: Patch vulnerability, rotate credentials
4. **Recover**: Restore from backups if needed
5. **Review**: Post-mortem and preventive measures

---

## Related Documentation

- [Configuration Guide](configuration.md) - Security configuration
- [PostgreSQL Setup](../operations/postgres-setup.md) - Database security
- [Deployment Guide](../operations/deployment.md) - Production deployment
- [Troubleshooting](troubleshooting.md) - Security-related issues

---

**Maintainers**: Somali NLP Contributors
**Security Contact**: [Open an issue](https://github.com/yourusername/somali-dialect-classifier/issues) for security concerns
